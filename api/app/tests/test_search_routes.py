from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

import uuid

import pytest

from app.core.config import settings
from app.ingestion.base import BaseConnector, ConnectorResult
from app.models.media import MediaItem, MediaType
from app.models.search_preview import ExternalSearchPreview
from app.services import search_preview_service
from sqlalchemy import select


class StubConnector(BaseConnector):
    def __init__(self, source_name: str, results: Iterable[ConnectorResult]) -> None:
        self.source_name = source_name
        self._results = [result for result in results]
        self._results_by_id = {result.source_id: result for result in self._results}

    async def search(self, query: str, limit: int = 3) -> list[str]:
        return [result.source_id for result in self._results][:limit]

    async def fetch(self, identifier: str) -> ConnectorResult:
        return self._results_by_id[identifier]


class FailingConnector(BaseConnector):
    def __init__(self, source_name: str) -> None:
        self.source_name = source_name

    async def search(self, query: str, limit: int = 3) -> list[str]:
        raise AssertionError(f"{self.source_name} connector should not have been called")

    async def fetch(self, identifier: str) -> ConnectorResult:
        raise AssertionError(f"{self.source_name} connector should not have been called")


async def _authenticate_for_external(client):
    suffix = uuid.uuid4().hex[:8]
    creds = {
        "email": f"search_{suffix}@example.com",
        "password": "search-pass123",
        "display_name": f"Search Tester {suffix}",
    }
    register_res = await client.post("/api/auth/register", json=creds)
    assert register_res.status_code == 200
    register_body = register_res.json()
    login_res = await client.post(
        "/api/auth/login",
        json={"email": creds["email"], "password": creds["password"]},
    )
    assert login_res.status_code == 200
    return register_body["user"]["id"]


@pytest.mark.asyncio
async def test_search_pagination_produces_metadata(client, session):
    media_titles = [f"Test Series {i}" for i in range(1, 7)]
    for title in media_titles:
        session.add(MediaItem(media_type=MediaType.MOVIE, title=title))
    await session.commit()

    response = await client.get("/api/search", params={"q": "Test", "page": 2, "per_page": 2})
    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["paging"]["total_internal"] == len(media_titles)
    assert payload["metadata"]["counts"]["internal"] == 2
    assert payload["metadata"]["source_counts"]["internal"] == 2
    assert len(payload["results"]) == 2
    assert payload["source"] == "internal"


@pytest.mark.asyncio
async def test_external_search_requires_auth(client):
    response = await client.get(
        "/api/search",
        params=[("q", "anon"), ("include_external", "true")],
    )
    assert response.status_code == 401
    assert "authentication" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_search_external_ingests_multi_source(client, monkeypatch, session):
    await _authenticate_for_external(client)
    session.add(MediaItem(media_type=MediaType.BOOK, title="Fan Query"))
    await session.commit()

    tmdb_results = [
        ConnectorResult(
            media_type=MediaType.MOVIE,
            title="TMDB Pick 1",
            description=None,
            release_date=None,
            cover_image_url=None,
            canonical_url=None,
            metadata={},
            source_name="tmdb",
            source_id="movie:9001",
            raw_payload={},
        ),
        ConnectorResult(
            media_type=MediaType.MOVIE,
            title="TMDB Pick 2",
            description=None,
            release_date=None,
            cover_image_url=None,
            canonical_url=None,
            metadata={},
            source_name="tmdb",
            source_id="movie:9002",
            raw_payload={},
        ),
    ]
    google_results = [
        ConnectorResult(
            media_type=MediaType.BOOK,
            title="Book Find 1",
            description=None,
            release_date=None,
            cover_image_url=None,
            canonical_url=None,
            metadata={},
            source_name="google_books",
            source_id="book:abc",
            raw_payload={},
        )
    ]
    connectors = {
        "google_books": StubConnector("google_books", google_results),
        "tmdb": StubConnector("tmdb", tmdb_results),
        "igdb": StubConnector("igdb", []),
        "lastfm": StubConnector("lastfm", []),
    }

    def _fake_get_connector(source: str) -> BaseConnector:
        try:
            return connectors[source.lower()]
        except KeyError as exc:
            raise ValueError(f"Unsupported source {source}") from exc

    monkeypatch.setattr("app.services.media_service.get_connector", _fake_get_connector)

    response = await client.get(
        "/api/search",
        params={"q": "Fan", "include_external": "true", "external_per_source": 2},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "internal+external"
    assert payload["metadata"]["counts"]["internal"] == 1
    assert payload["metadata"]["counts"]["external_ingested"] == 3
    assert payload["metadata"]["source_counts"]["external"] == 3
    assert payload["metadata"]["source_counts"]["tmdb"] == 2
    assert payload["metadata"]["source_counts"]["google_books"] == 1
    assert len(payload["results"]) >= 4


@pytest.mark.asyncio
async def test_search_sources_filter_limits_external_only(client, monkeypatch, session):
    await _authenticate_for_external(client)
    tmdb_results = [
        ConnectorResult(
            media_type=MediaType.MOVIE,
            title="TMDB Pick 1",
            description=None,
            release_date=None,
            cover_image_url=None,
            canonical_url=None,
            metadata={},
            source_name="tmdb",
            source_id="movie:9001",
            raw_payload={},
        ),
        ConnectorResult(
            media_type=MediaType.MOVIE,
            title="TMDB Pick 2",
            description=None,
            release_date=None,
            cover_image_url=None,
            canonical_url=None,
            metadata={},
            source_name="tmdb",
            source_id="movie:9002",
            raw_payload={},
        ),
    ]
    connectors = {
        "tmdb": StubConnector("tmdb", tmdb_results),
        "google_books": StubConnector("google_books", []),
        "igdb": StubConnector("igdb", []),
        "lastfm": StubConnector("lastfm", []),
    }

    def _fake_get_connector(source: str) -> BaseConnector:
        return connectors[source]

    monkeypatch.setattr("app.services.media_service.get_connector", _fake_get_connector)

    response = await client.get(
        "/api/search",
        params=[("q", "Fan"), ("sources", "tmdb"), ("external_per_source", "2")],
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "external"
    assert payload["metadata"]["counts"]["internal"] == 0
    assert payload["metadata"]["source_counts"]["internal"] == 0
    assert payload["metadata"]["source_counts"]["tmdb"] == 2
    assert "google_books" not in payload["metadata"]["source_counts"]


@pytest.mark.asyncio
async def test_search_types_filter_drops_incompatible_sources(client, monkeypatch, session):
    await _authenticate_for_external(client)
    session.add(MediaItem(media_type=MediaType.BOOK, title="Fan Query"))
    session.add(MediaItem(media_type=MediaType.MOVIE, title="Fan Query 2"))
    await session.commit()

    connectors = {
        "google_books": StubConnector(
            "google_books",
            [
                ConnectorResult(
                    media_type=MediaType.BOOK,
                    title="Book Find 1",
                    description=None,
                    release_date=None,
                    cover_image_url=None,
                    canonical_url=None,
                    metadata={},
                    source_name="google_books",
                    source_id="book:abc",
                    raw_payload={},
                )
            ],
        ),
        "tmdb": FailingConnector("tmdb"),
        "igdb": FailingConnector("igdb"),
        "lastfm": FailingConnector("lastfm"),
    }

    def _fake_get_connector(source: str) -> BaseConnector:
        return connectors[source]

    monkeypatch.setattr("app.services.media_service.get_connector", _fake_get_connector)

    response = await client.get(
        "/api/search",
        params=[
            ("q", "Fan"),
            ("include_external", "true"),
            ("external_per_source", "1"),
            ("types", "book"),
        ],
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["counts"]["internal"] == 1
    assert payload["metadata"]["source_counts"]["internal"] == 1
    assert payload["metadata"]["source_counts"]["google_books"] == 1
    assert "tmdb" not in payload["metadata"]["source_counts"]
    assert payload["source"] == "internal+external"


@pytest.mark.asyncio
async def test_search_external_per_source_limits_counts(client, monkeypatch, session):
    await _authenticate_for_external(client)
    session.add(MediaItem(media_type=MediaType.BOOK, title="Fan Query"))
    await session.commit()

    tmdb_results = [
        ConnectorResult(
            media_type=MediaType.MOVIE,
            title="TMDB Pick 1",
            description=None,
            release_date=None,
            cover_image_url=None,
            canonical_url=None,
            metadata={},
            source_name="tmdb",
            source_id="movie:9001",
            raw_payload={},
        ),
        ConnectorResult(
            media_type=MediaType.MOVIE,
            title="TMDB Pick 2",
            description=None,
            release_date=None,
            cover_image_url=None,
            canonical_url=None,
            metadata={},
            source_name="tmdb",
            source_id="movie:9002",
            raw_payload={},
        ),
    ]
    google_results = [
        ConnectorResult(
            media_type=MediaType.BOOK,
            title="Book Find 1",
            description=None,
            release_date=None,
            cover_image_url=None,
            canonical_url=None,
            metadata={},
            source_name="google_books",
            source_id="book:abc",
            raw_payload={},
        ),
        ConnectorResult(
            media_type=MediaType.BOOK,
            title="Book Find 2",
            description=None,
            release_date=None,
            cover_image_url=None,
            canonical_url=None,
            metadata={},
            source_name="google_books",
            source_id="book:def",
            raw_payload={},
        ),
    ]
    connectors = {
        "google_books": StubConnector("google_books", google_results),
        "tmdb": StubConnector("tmdb", tmdb_results),
        "igdb": StubConnector("igdb", []),
        "lastfm": StubConnector("lastfm", []),
    }

    def _fake_get_connector(source: str) -> BaseConnector:
        return connectors[source]

    monkeypatch.setattr("app.services.media_service.get_connector", _fake_get_connector)

    response = await client.get(
        "/api/search",
        params=[
            ("q", "Fan"),
            ("include_external", "true"),
            ("external_per_source", "1"),
        ],
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["counts"]["internal"] == 1
    assert payload["metadata"]["counts"]["external_ingested"] == 2
    assert payload["metadata"]["source_counts"]["external"] == 2
    assert payload["metadata"]["source_counts"]["tmdb"] == 1
    assert payload["metadata"]["source_counts"]["google_books"] == 1
    assert len(payload["results"]) >= 3


@pytest.mark.asyncio
async def test_search_external_dedupes_against_internal_and_tracks_metrics(client, monkeypatch, session):
    await _authenticate_for_external(client)
    existing = MediaItem(
        media_type=MediaType.MOVIE,
        title="Shared Hit",
        canonical_url="https://www.themoviedb.org/movie/42",
    )
    session.add(existing)
    await session.commit()

    tmdb_results = [
        ConnectorResult(
            media_type=MediaType.MOVIE,
            title="Shared Hit",
            description=None,
            release_date=None,
            cover_image_url=None,
            canonical_url="https://www.themoviedb.org/movie/42",
            metadata={},
            source_name="tmdb",
            source_id="movie:42",
            raw_payload={},
        ),
        ConnectorResult(
            media_type=MediaType.MOVIE,
            title="Different Hit",
            description=None,
            release_date=None,
            cover_image_url=None,
            canonical_url="https://www.themoviedb.org/movie/99",
            metadata={},
            source_name="tmdb",
            source_id="movie:99",
            raw_payload={},
        ),
    ]
    google_results = [
        ConnectorResult(
            media_type=MediaType.BOOK,
            title="Book Match",
            description=None,
            release_date=None,
            cover_image_url=None,
            canonical_url="https://books.google.com/book?id=abc",
            metadata={},
            source_name="google_books",
            source_id="book:abc",
            raw_payload={},
        )
    ]
    connectors = {
        "tmdb": StubConnector("tmdb", tmdb_results),
        "google_books": StubConnector("google_books", google_results),
    }

    def _fake_get_connector(source: str) -> BaseConnector:
        return connectors[source]

    monkeypatch.setattr("app.services.media_service.get_connector", _fake_get_connector)

    response = await client.get(
        "/api/search",
        params=[
            ("q", "Shared"),
            ("include_external", "true"),
            ("external_per_source", "2"),
            ("sources", "tmdb"),
            ("sources", "google_books"),
        ],
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "internal+external"
    assert payload["results"][0]["id"] == str(existing.id)
    assert payload["metadata"]["counts"]["internal"] == 1
    assert payload["metadata"]["counts"]["external_ingested"] == 2
    assert payload["metadata"]["counts"]["external_deduped"] == 1
    assert payload["metadata"]["source_counts"]["tmdb"] == 1
    assert payload["metadata"]["source_counts"]["google_books"] == 1
    tmdb_metrics = payload["metadata"]["source_metrics"]["tmdb"]
    assert tmdb_metrics["deduped"] == 1
    assert isinstance(tmdb_metrics["search_ms"], (int, float))
    assert isinstance(tmdb_metrics["fetch_ms"], (int, float))
    assert len(payload["results"]) == 3


@pytest.mark.asyncio
async def test_search_merge_order_follows_source_order(client, monkeypatch, session):
    await _authenticate_for_external(client)
    connectors = {
        "tmdb": StubConnector(
            "tmdb",
            [
                ConnectorResult(
                    media_type=MediaType.MOVIE,
                    title="Zeta Movie",
                    description=None,
                    release_date=None,
                    cover_image_url=None,
                    canonical_url="https://www.themoviedb.org/movie/zeta",
                    metadata={},
                    source_name="tmdb",
                    source_id="movie:zeta",
                    raw_payload={},
                )
            ],
        ),
        "google_books": StubConnector(
            "google_books",
            [
                ConnectorResult(
                    media_type=MediaType.BOOK,
                    title="Alpha Book",
                    description=None,
                    release_date=None,
                    cover_image_url=None,
                    canonical_url="https://books.google.com/book?id=alpha",
                    metadata={},
                    source_name="google_books",
                    source_id="book:alpha",
                    raw_payload={},
                )
            ],
        ),
    }

    def _fake_get_connector(source: str) -> BaseConnector:
        return connectors[source]

    monkeypatch.setattr("app.services.media_service.get_connector", _fake_get_connector)

    response = await client.get(
        "/api/search",
        params=[
            ("q", "Order"),
            ("sources", "tmdb"),
            ("sources", "google_books"),
            ("external_per_source", "1"),
        ],
    )
    assert response.status_code == 200
    payload = response.json()
    titles = [item["title"] for item in payload["results"]]
    assert titles[:2] == ["Zeta Movie", "Alpha Book"]
    assert payload["metadata"]["source_counts"]["tmdb"] == 1
    assert payload["metadata"]["source_counts"]["google_books"] == 1
    assert payload["metadata"]["source_metrics"]["tmdb"]["returned"] == 1


@pytest.mark.asyncio
async def test_search_external_previews_cached(session, client, monkeypatch):
    user_id = uuid.UUID(await _authenticate_for_external(client))
    connectors = {
        "tmdb": StubConnector(
            "tmdb",
            [
                ConnectorResult(
                    media_type=MediaType.MOVIE,
                    title="Preview Cache",
                    description=None,
                    release_date=None,
                    cover_image_url=None,
                    canonical_url="https://www.themoviedb.org/movie/cache",
                    metadata={},
                    source_name="tmdb",
                    source_id="movie:cache",
                    raw_payload={},
                )
            ],
        ),
        "google_books": StubConnector("google_books", []),
        "igdb": StubConnector("igdb", []),
        "lastfm": StubConnector("lastfm", []),
    }

    def _fake_get_connector(source: str) -> BaseConnector:
        return connectors[source]

    monkeypatch.setattr("app.services.media_service.get_connector", _fake_get_connector)

    response = await client.get(
        "/api/search",
        params=[
            ("q", "Cache"),
            ("include_external", "true"),
            ("external_per_source", "1"),
        ],
    )
    assert response.status_code == 200

    statement = select(ExternalSearchPreview).where(
        ExternalSearchPreview.user_id == user_id,
        ExternalSearchPreview.source_name == "tmdb",
        ExternalSearchPreview.external_id == "movie:cache",
    )
    stored = await session.execute(statement)
    preview = stored.scalar_one_or_none()
    assert preview is not None
    assert preview.expires_at > datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_search_external_quota_enforced(client, monkeypatch):
    await _authenticate_for_external(client)
    monkeypatch.setattr(settings, "external_search_quota_max_requests", 2)

    class FixedDatetime:
        @classmethod
        def utcnow(cls):
            return datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        @classmethod
        def utcfromtimestamp(cls, _: float):
            return datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(search_preview_service, "datetime", FixedDatetime)

    connectors = {
        "tmdb": StubConnector(
            "tmdb",
            [
                ConnectorResult(
                    media_type=MediaType.MOVIE,
                    title="Quota Movie",
                    description=None,
                    release_date=None,
                    cover_image_url=None,
                    canonical_url="https://www.themoviedb.org/movie/quota",
                    metadata={},
                    source_name="tmdb",
                    source_id="movie:quota",
                    raw_payload={},
                )
            ],
        ),
        "google_books": StubConnector("google_books", []),
        "igdb": StubConnector("igdb", []),
        "lastfm": StubConnector("lastfm", []),
    }

    def _fake_get_connector(source: str) -> BaseConnector:
        return connectors[source]

    monkeypatch.setattr("app.services.media_service.get_connector", _fake_get_connector)

    for _ in range(2):
        response = await client.get(
            "/api/search",
            params=[("q", "Quota"), ("include_external", "true"), ("external_per_source", "1")],
        )
        assert response.status_code == 200

    rate_limited = await client.get(
        "/api/search",
        params=[("q", "Quota"), ("include_external", "true"), ("external_per_source", "1")],
    )
    assert rate_limited.status_code == 429
    detail = rate_limited.json().get("detail", "")
    assert "quota" in detail.lower()
