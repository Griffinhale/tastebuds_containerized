"""Connector tests for TMDB auth logic and error handling."""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.ingestion.http import ExternalAPIError
from app.ingestion.tmdb import TMDBConnector


def test_tmdb_auth_prefers_bearer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "tmdb_api_auth_header", "preferred-token")
    monkeypatch.setattr(settings, "tmdb_api_key", "api-key")

    connector = TMDBConnector()
    headers, params = connector._auth()

    assert headers["Authorization"] == "Bearer preferred-token"
    assert "api_key" not in params


def test_tmdb_auth_uses_api_key_when_header_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "tmdb_api_auth_header", None)
    monkeypatch.setattr(settings, "tmdb_api_key", "api-key")

    connector = TMDBConnector()
    headers, params = connector._auth()

    assert "Authorization" not in headers
    assert params["api_key"] == "api-key"


def test_tmdb_auth_errors_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "tmdb_api_auth_header", None)
    monkeypatch.setattr(settings, "tmdb_api_key", None)

    connector = TMDBConnector()
    with pytest.raises(ExternalAPIError):
        connector._auth()
