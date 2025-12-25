from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.ingestion.base import ConnectorResult
from app.models.media import MediaSource, MediaType
from app.services import media_service


@pytest.mark.asyncio
async def test_upsert_media_truncates_payloads(session, monkeypatch):
    monkeypatch.setattr(settings, "ingestion_payload_max_bytes", 50)
    monkeypatch.setattr(settings, "ingestion_metadata_max_bytes", 20)
    connector_result = ConnectorResult(
        media_type=MediaType.MOVIE,
        title="Huge payload",
        description=None,
        release_date=None,
        cover_image_url=None,
        canonical_url=None,
        metadata={"meta": "x" * 200},
        source_name="tmdb",
        source_id=str(uuid.uuid4()),
        raw_payload={"big": "y" * 500},
    )

    media = await media_service.upsert_media(session, connector_result)
    assert media.metadata.get("truncated") is True
    sources = await session.execute(
        select(MediaSource).where(MediaSource.media_item_id == media.id, MediaSource.source_name == "tmdb")
    )
    source = sources.scalar_one()
    assert source.raw_payload.get("truncated") is True
    assert source.raw_payload.get("reason") == "raw_ingestion_payload_too_large"
