from __future__ import annotations

import pytest

from app.ingestion.base import ConnectorResult
from app.models.media import MediaItem, MediaType
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
