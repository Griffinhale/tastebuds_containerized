from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.core.config import settings
from app.models.media import MediaItem, MediaSource, MediaType
from app.services import media_service


@pytest.mark.asyncio
async def test_prune_media_source_payloads_strips_old_rows(session, monkeypatch):
    monkeypatch.setattr(settings, "ingestion_payload_retention_days", 30)
    old_item = MediaItem(media_type=MediaType.BOOK, title="Old Title", description="old")
    new_item = MediaItem(media_type=MediaType.BOOK, title="New Title", description="new")
    session.add_all([old_item, new_item])
    await session.flush()

    old_source = MediaSource(
        media_item_id=old_item.id,
        source_name="google_books",
        external_id="old-1",
        raw_payload={"keep": False},
        fetched_at=datetime.utcnow() - timedelta(days=45),
    )
    fresh_source = MediaSource(
        media_item_id=new_item.id,
        source_name="google_books",
        external_id="new-1",
        raw_payload={"keep": True},
        fetched_at=datetime.utcnow(),
    )
    session.add_all([old_source, fresh_source])
    await session.commit()

    stripped = await media_service.prune_media_source_payloads(session)
    assert stripped == 1

    refreshed_old = await session.get(MediaSource, old_source.id)
    assert refreshed_old
    assert refreshed_old.raw_payload.get("redacted") is True
    assert refreshed_old.raw_payload.get("reason") == "retention_expired"

    refreshed_new = await session.get(MediaSource, fresh_source.id)
    assert refreshed_new
    assert refreshed_new.raw_payload == {"keep": True}


@pytest.mark.asyncio
async def test_prune_media_source_payloads_can_be_disabled(session, monkeypatch):
    monkeypatch.setattr(settings, "ingestion_payload_retention_days", 0)
    item = MediaItem(media_type=MediaType.MOVIE, title="No retention", description="payload")
    session.add(item)
    await session.flush()
    source = MediaSource(
        media_item_id=item.id,
        source_name="tmdb",
        external_id="noop",
        raw_payload={"should": "stay"},
        fetched_at=datetime.utcnow() - timedelta(days=400),
    )
    session.add(source)
    await session.commit()

    stripped = await media_service.prune_media_source_payloads(session)
    assert stripped == 0

    refreshed = await session.get(MediaSource, source.id)
    assert refreshed
    assert refreshed.raw_payload == {"should": "stay"}
