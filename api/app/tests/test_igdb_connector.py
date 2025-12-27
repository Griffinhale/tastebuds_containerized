"""Connector tests for IGDB auth, parsing, and mapping behavior."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta
from typing import Any

import httpx
import pytest

from app.core.config import settings
from app.ingestion.igdb import IGDBConnector

TOKEN_URL = IGDBConnector._token_url
GAME_URL = IGDBConnector._game_url


def _build_response(url: str, *, status: int = 200, json_data: Any | None = None) -> httpx.Response:
    request = httpx.Request("POST", url)
    return httpx.Response(status_code=status, json=json_data or {}, request=request)


def _make_async_client(responses: deque[httpx.Response], call_log: list[str]) -> type[httpx.AsyncClient]:
    class DummyAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self._responses = responses

        async def __aenter__(self) -> DummyAsyncClient:
            return self

        async def __aexit__(self, *args: Any) -> bool:
            return False

        async def post(self, url: str, **kwargs: Any) -> httpx.Response:
            call_log.append(url)
            if not self._responses:
                raise RuntimeError("No stub responses configured")
            return self._responses.popleft()

    return DummyAsyncClient


def _configure_connector(
    monkeypatch: pytest.MonkeyPatch, responses: deque[httpx.Response]
) -> tuple[IGDBConnector, list[str]]:
    call_log: list[str] = []
    DummyClient = _make_async_client(responses, call_log)
    monkeypatch.setattr("app.ingestion.igdb.httpx.AsyncClient", DummyClient)
    monkeypatch.setattr(settings, "igdb_client_id", "example-id")
    monkeypatch.setattr(settings, "igdb_client_secret", "example-secret")
    connector = IGDBConnector()
    return connector, call_log


@pytest.mark.asyncio
async def test_igdb_token_cached_until_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = deque(
        [
            _build_response(TOKEN_URL, json_data={"access_token": "cached", "expires_in": 300}),
        ]
    )
    connector, call_log = _configure_connector(monkeypatch, responses)

    token = await connector._ensure_token()
    assert token == "cached"

    cached_again = await connector._ensure_token()
    assert cached_again == "cached"
    assert call_log == [TOKEN_URL]


@pytest.mark.asyncio
async def test_igdb_token_refreshes_when_expired(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = deque(
        [
            _build_response(TOKEN_URL, json_data={"access_token": "refreshed", "expires_in": 300}),
        ]
    )
    connector, call_log = _configure_connector(monkeypatch, responses)
    connector._access_token = "stale"
    connector._token_expires_at = datetime.utcnow() - timedelta(seconds=1)

    token = await connector._ensure_token()
    assert token == "refreshed"
    assert call_log == [TOKEN_URL]


@pytest.mark.asyncio
async def test_igdb_fetch_retries_after_401(monkeypatch: pytest.MonkeyPatch) -> None:
    success_payload = [
        {
            "id": 42,
            "name": "Resilience Game",
            "summary": "Retryable release",
            "first_release_date": 1_600_000_000,
            "cover": {"url": "https://cover"},
            "genres": [{"name": "Action"}],
            "platforms": [{"name": "PC"}],
            "slug": "resilience-game",
            "involved_companies": [
                {"company": {"name": "House Studios"}, "developer": True},
                {"company": {"name": "Big Publisher"}, "publisher": True},
            ],
        }
    ]
    responses = deque(
        [
            _build_response(TOKEN_URL, json_data={"access_token": "initial", "expires_in": 60}),
            _build_response(GAME_URL, status=401),
            _build_response(TOKEN_URL, json_data={"access_token": "refreshed", "expires_in": 60}),
            _build_response(GAME_URL, json_data=success_payload),
        ]
    )
    connector, call_log = _configure_connector(monkeypatch, responses)

    result = await connector.fetch("123")
    assert result.source_id == "42"
    assert result.source_name == "igdb"
    assert connector._access_token == "refreshed"
    assert call_log == [TOKEN_URL, GAME_URL, TOKEN_URL, GAME_URL]
