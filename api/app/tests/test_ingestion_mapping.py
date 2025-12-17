from __future__ import annotations

import pytest

from app.ingestion.base import ConnectorResult
from app.models.media import MediaItem, MediaType
from app.samples import load_ingestion_sample
from app.services import media_service


@pytest.mark.asyncio
async def test_book_ingestion_populates_extension(session):
    media = MediaItem(media_type=MediaType.BOOK, title="Placeholder")
    session.add(media)
    await session.commit()
    result = ConnectorResult(
        media_type=MediaType.BOOK,
        title="Deep Work",
        description="",
        release_date=None,
        cover_image_url=None,
        canonical_url=None,
        metadata={"categories": ["Productivity"]},
        source_name="test_source",
        source_id="book-1",
        raw_payload={"mock": True},
        extensions={
            "book": {
                "authors": ["Cal Newport"],
                "page_count": 256,
                "publisher": "Grand Central",
                "language": "en",
                "isbn_10": "1455586692",
                "isbn_13": "9781455586691",
            }
        },
    )
    stored = await media_service.upsert_media(session, result, force_refresh=True)
    assert stored.book is not None
    assert stored.book.isbn_13 == "9781455586691"
    assert stored.metadata["categories"] == ["Productivity"]


@pytest.mark.asyncio
async def test_movie_ingestion_populates_extension(session):
    result = ConnectorResult(
        media_type=MediaType.MOVIE,
        title="Cinematic Journeys",
        description="Anthology of visionary films",
        release_date=None,
        cover_image_url="https://image.tmdb.org/t/p/original/cinematic-journeys.jpg",
        canonical_url="https://www.themoviedb.org/movie/603",
        metadata={
            "genres": ["Drama", "Adventure"],
            "languages": [{"english_name": "English", "iso_639_1": "en", "name": "English"}],
            "status": "Released",
        },
        source_name="tmdb",
        source_id="603",
        raw_payload=load_ingestion_sample("tmdb_movie"),
        extensions={
            "movie": {
                "runtime_minutes": 138,
                "directors": ["T. Laird"],
                "producers": ["C. Fields", "H. Sen"],
                "tmdb_type": "movie",
            }
        },
    )
    stored = await media_service.upsert_media(session, result, force_refresh=True)
    assert stored.movie is not None
    assert stored.movie.runtime_minutes == 138
    assert stored.movie.directors == ["T. Laird"]
    assert stored.metadata["status"] == "Released"


@pytest.mark.asyncio
async def test_game_ingestion_populates_extension(session):
    result = ConnectorResult(
        media_type=MediaType.GAME,
        title="Quest for Flavor",
        description="Indie narrative adventure",
        release_date=None,
        cover_image_url="https://images.igdb.com/igdb/image/upload/t_cover_big/demo-cover.jpg",
        canonical_url=None,
        metadata={
            "genres": ["Adventure"],
            "platforms": ["PC (Microsoft Windows)", "Nintendo Switch"],
        },
        source_name="igdb",
        source_id="7346",
        raw_payload=load_ingestion_sample("igdb_game"),
        extensions={
            "game": {
                "platforms": ["PC", "Switch"],
                "developers": ["Calico Works"],
                "publishers": ["Calico Works"],
                "genres": ["Adventure"],
            }
        },
    )
    stored = await media_service.upsert_media(session, result, force_refresh=True)
    assert stored.game is not None
    assert stored.game.platforms == ["PC", "Switch"]
    assert stored.game.developers == ["Calico Works"]
    assert stored.metadata["platforms"] == ["PC (Microsoft Windows)", "Nintendo Switch"]


@pytest.mark.asyncio
async def test_music_ingestion_populates_extension(session):
    result = ConnectorResult(
        media_type=MediaType.MUSIC,
        title="Soundtrack of Curiosity",
        description="An ambient score",
        release_date=None,
        cover_image_url="https://last.fm/demo-cover.jpg",
        canonical_url="https://www.last.fm/music/Nia+Holloway/_/Soundtrack+of+Curiosity",
        metadata={
            "listeners": "12000",
            "playcount": "48000",
            "tags": ["ambient", "focus"],
        },
        source_name="lastfm",
        source_id="demo-track-curiosity",
        raw_payload=load_ingestion_sample("lastfm_track"),
        extensions={
            "music": {
                "artist_name": "Nia Holloway",
                "album_name": "Resonant Paths",
                "track_number": 3,
                "duration_ms": 226000,
            }
        },
    )
    stored = await media_service.upsert_media(session, result, force_refresh=True)
    assert stored.music is not None
    assert stored.music.artist_name == "Nia Holloway"
    assert stored.music.duration_ms == 226000
    assert stored.metadata["tags"] == ["ambient", "focus"]
