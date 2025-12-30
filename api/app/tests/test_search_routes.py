"""Tests for search routes, preview caching, and connector gating."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Iterable

import pytest
import pytest_asyncio
from sqlalchemy import select, text

from app.core.config import settings
from app.ingestion.base import BaseConnector, ConnectorResult
from app.models.media import BookItem, MediaItem, MediaType, MusicItem
from app.models.search_preview import ExternalSearchPreview
from app.services import search_preview_service


@pytest_asyncio.fixture(autouse=True)
async def _setup_search_fts(session):
    if session.bind.dialect.name != "postgresql":
        yield
        return

    schema_translate_map = None
    if session.bind and hasattr(session.bind, "sync_engine"):
        schema_translate_map = session.bind.sync_engine._execution_options.get("schema_translate_map")
    schema_name = schema_translate_map.get(None) if schema_translate_map else None
    if not schema_name:
        schema_result = await session.execute(
            text(
                "SELECT table_schema FROM information_schema.tables "
                "WHERE table_name = 'media_items' LIMIT 1"
            )
        )
        schema_name = schema_result.scalar_one()
    schema_prefix = f'"{schema_name}"'

    await session.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent"))
    await session.execute(
        text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'english_unaccent') THEN
                    CREATE TEXT SEARCH CONFIGURATION english_unaccent ( COPY = english );
                    ALTER TEXT SEARCH CONFIGURATION english_unaccent
                        ALTER MAPPING FOR asciiword, asciihword, hword_asciipart, word, hword, hword_part
                        WITH unaccent, english_stem;
                END IF;
            END $$;
            """
        )
    )
    await session.execute(
        text(
            f"""
            CREATE OR REPLACE FUNCTION {schema_prefix}.media_items_search_vector(target_id uuid)
            RETURNS tsvector
            LANGUAGE sql
            STABLE
            AS $$
            SELECT
                setweight(to_tsvector('english_unaccent', coalesce(mi.title, '')), 'A') ||
                setweight(to_tsvector('english_unaccent', coalesce(mi.subtitle, '')), 'B') ||
                setweight(to_tsvector('english_unaccent', coalesce(mi.description, '')), 'C') ||
                setweight(
                    (
                        to_tsvector(
                            'english_unaccent',
                            coalesce(
                                array_to_string(
                                    ARRAY(SELECT jsonb_array_elements_text(coalesce(b.authors, '[]'::jsonb))),
                                    ' '
                                ),
                                ''
                            )
                        ) ||
                        to_tsvector('english_unaccent', coalesce(b.publisher, '')) ||
                        to_tsvector('english_unaccent', coalesce(b.isbn_10, '')) ||
                        to_tsvector('english_unaccent', coalesce(b.isbn_13, '')) ||
                        to_tsvector(
                            'english_unaccent',
                            coalesce(
                                array_to_string(
                                    ARRAY(SELECT jsonb_array_elements_text(coalesce(mo.directors, '[]'::jsonb))),
                                    ' '
                                ),
                                ''
                            )
                        ) ||
                        to_tsvector(
                            'english_unaccent',
                            coalesce(
                                array_to_string(
                                    ARRAY(SELECT jsonb_array_elements_text(coalesce(mo.producers, '[]'::jsonb))),
                                    ' '
                                ),
                                ''
                            )
                        ) ||
                        to_tsvector(
                            'english_unaccent',
                            coalesce(
                                array_to_string(
                                    ARRAY(SELECT jsonb_array_elements_text(coalesce(g.developers, '[]'::jsonb))),
                                    ' '
                                ),
                                ''
                            )
                        ) ||
                        to_tsvector(
                            'english_unaccent',
                            coalesce(
                                array_to_string(
                                    ARRAY(SELECT jsonb_array_elements_text(coalesce(g.publishers, '[]'::jsonb))),
                                    ' '
                                ),
                                ''
                            )
                        ) ||
                        to_tsvector(
                            'english_unaccent',
                            coalesce(
                                array_to_string(
                                    ARRAY(SELECT jsonb_array_elements_text(coalesce(g.genres, '[]'::jsonb))),
                                    ' '
                                ),
                                ''
                            )
                        ) ||
                        to_tsvector(
                            'english_unaccent',
                            coalesce(
                                array_to_string(
                                    ARRAY(SELECT jsonb_array_elements_text(coalesce(g.platforms, '[]'::jsonb))),
                                    ' '
                                ),
                                ''
                            )
                        ) ||
                        to_tsvector('english_unaccent', coalesce(mu.artist_name, '')) ||
                        to_tsvector('english_unaccent', coalesce(mu.album_name, ''))
                    ),
                    'D'
                )
            FROM {schema_prefix}.media_items mi
            LEFT JOIN {schema_prefix}.book_items b ON b.media_item_id = mi.id
            LEFT JOIN {schema_prefix}.movie_items mo ON mo.media_item_id = mi.id
            LEFT JOIN {schema_prefix}.game_items g ON g.media_item_id = mi.id
            LEFT JOIN {schema_prefix}.music_items mu ON mu.media_item_id = mi.id
            WHERE mi.id = target_id;
            $$;
            """
        )
    )
    await session.execute(
        text(
            f"""
            CREATE OR REPLACE FUNCTION {schema_prefix}.refresh_media_item_search_vector(target_id uuid)
            RETURNS void
            LANGUAGE sql
            AS $$
            UPDATE {schema_prefix}.media_items
            SET search_vector = {schema_prefix}.media_items_search_vector(target_id)
            WHERE id = target_id;
            $$;
            """
        )
    )
    await session.execute(
        text(
            f"""
            CREATE OR REPLACE FUNCTION {schema_prefix}.media_items_search_vector_trigger()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            DECLARE
                target_id uuid;
            BEGIN
                IF TG_OP = 'DELETE' THEN
                    target_id := OLD.media_item_id;
                ELSIF TG_TABLE_NAME = 'media_items' THEN
                    target_id := NEW.id;
                ELSE
                    target_id := NEW.media_item_id;
                END IF;
                IF target_id IS NULL THEN
                    IF TG_OP = 'DELETE' THEN
                        RETURN OLD;
                    END IF;
                    RETURN NEW;
                END IF;
                PERFORM {schema_prefix}.refresh_media_item_search_vector(target_id);
                IF TG_OP = 'DELETE' THEN
                    RETURN OLD;
                END IF;
                RETURN NEW;
            END;
            $$;
            """
        )
    )
    await session.execute(
        text(f"DROP TRIGGER IF EXISTS media_items_search_vector_update ON {schema_prefix}.media_items")
    )
    await session.execute(
        text(
            f"""
            CREATE TRIGGER media_items_search_vector_update
            AFTER INSERT OR UPDATE OF title, subtitle, description
            ON {schema_prefix}.media_items
            FOR EACH ROW EXECUTE FUNCTION {schema_prefix}.media_items_search_vector_trigger();
            """
        )
    )
    await session.execute(
        text(f"DROP TRIGGER IF EXISTS book_items_search_vector_update ON {schema_prefix}.book_items")
    )
    await session.execute(
        text(
            f"""
            CREATE TRIGGER book_items_search_vector_update
            AFTER INSERT OR UPDATE OR DELETE
            ON {schema_prefix}.book_items
            FOR EACH ROW EXECUTE FUNCTION {schema_prefix}.media_items_search_vector_trigger();
            """
        )
    )
    await session.execute(
        text(f"DROP TRIGGER IF EXISTS movie_items_search_vector_update ON {schema_prefix}.movie_items")
    )
    await session.execute(
        text(
            f"""
            CREATE TRIGGER movie_items_search_vector_update
            AFTER INSERT OR UPDATE OR DELETE
            ON {schema_prefix}.movie_items
            FOR EACH ROW EXECUTE FUNCTION {schema_prefix}.media_items_search_vector_trigger();
            """
        )
    )
    await session.execute(
        text(f"DROP TRIGGER IF EXISTS game_items_search_vector_update ON {schema_prefix}.game_items")
    )
    await session.execute(
        text(
            f"""
            CREATE TRIGGER game_items_search_vector_update
            AFTER INSERT OR UPDATE OR DELETE
            ON {schema_prefix}.game_items
            FOR EACH ROW EXECUTE FUNCTION {schema_prefix}.media_items_search_vector_trigger();
            """
        )
    )
    await session.execute(
        text(f"DROP TRIGGER IF EXISTS music_items_search_vector_update ON {schema_prefix}.music_items")
    )
    await session.execute(
        text(
            f"""
            CREATE TRIGGER music_items_search_vector_update
            AFTER INSERT OR UPDATE OR DELETE
            ON {schema_prefix}.music_items
            FOR EACH ROW EXECUTE FUNCTION {schema_prefix}.media_items_search_vector_trigger();
            """
        )
    )
    await session.execute(
        text(
            f"""
            UPDATE {schema_prefix}.media_items
            SET search_vector = {schema_prefix}.media_items_search_vector(id);
            """
        )
    )
    await session.commit()
    yield


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
async def test_search_matches_creator_and_description(client, session):
    book = MediaItem(
        media_type=MediaType.BOOK,
        title="Left Hand of Darkness",
        description="Icebound world of winter and shifting loyalties.",
    )
    music = MediaItem(
        media_type=MediaType.MUSIC,
        title="Kind of Blue",
        description="Classic jazz album with modal improvisation.",
    )
    session.add_all([book, music])
    await session.flush()
    session.add(
        BookItem(
            media_item_id=book.id,
            authors=["Ursula K. Le Guin"],
            publisher="Ace",
        )
    )
    session.add(
        MusicItem(
            media_item_id=music.id,
            artist_name="Miles Davis",
            album_name="Kind of Blue",
        )
    )
    await session.commit()

    response = await client.get("/api/search", params={"q": "Ursula"})
    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["results"]]
    assert "Left Hand of Darkness" in titles

    response = await client.get("/api/search", params={"q": "Miles"})
    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["results"]]
    assert "Kind of Blue" in titles

    response = await client.get("/api/search", params={"q": "icebound"})
    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["results"]]
    assert "Left Hand of Darkness" in titles


@pytest.mark.asyncio
async def test_search_ranking_prioritizes_title_over_metadata(client, session):
    title_hit = MediaItem(media_type=MediaType.BOOK, title="Zeta Atlas")
    metadata_hit = MediaItem(media_type=MediaType.BOOK, title="Alpha Story")
    session.add_all([title_hit, metadata_hit])
    await session.flush()
    session.add(BookItem(media_item_id=metadata_hit.id, authors=["Atlas Explorer"]))
    await session.commit()

    response = await client.get("/api/search", params={"q": "Atlas"})
    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["results"]]
    assert titles[0] == "Zeta Atlas"


@pytest.mark.asyncio
async def test_search_handles_diacritics_and_punctuation(client, session):
    session.add(MediaItem(media_type=MediaType.BOOK, title="Café Noir"))
    await session.commit()

    response = await client.get("/api/search", params={"q": "Cafe"})
    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["results"]]
    assert "Café Noir" in titles

    response = await client.get("/api/search", params={"q": "\"Cafe"})
    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["results"]]
    assert "Café Noir" in titles


@pytest.mark.asyncio
async def test_search_vector_refreshes_after_extension_update(client, session):
    book = MediaItem(media_type=MediaType.BOOK, title="Memory Line")
    session.add(book)
    await session.flush()
    session.add(BookItem(media_item_id=book.id, authors=["Old Name"]))
    await session.commit()

    response = await client.get("/api/search", params={"q": "Old"})
    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["results"]]
    assert "Memory Line" in titles

    result = await session.execute(select(BookItem).where(BookItem.media_item_id == book.id))
    book_item = result.scalar_one()
    book_item.authors = ["New Name"]
    await session.commit()

    response = await client.get("/api/search", params={"q": "New"})
    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["results"]]
    assert "Memory Line" in titles


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
