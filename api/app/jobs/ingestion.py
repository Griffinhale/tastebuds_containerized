from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.db.session import async_session
from app.schema.media import MediaItemDetail
from app.services import media_service

logger = logging.getLogger("app.jobs.ingestion")


def ingest_media_job(*, source: str, identifier: str, force_refresh: bool = False) -> dict[str, Any]:
    """Enqueue-able ingestion job."""

    async def _run() -> dict[str, Any]:
        async with async_session() as session:
            media_item = await media_service.ingest_from_source(
                session, source=source, identifier=identifier, force_refresh=force_refresh
            )
            hydrated = await media_service.get_media_with_sources(session, media_item.id)
            detail = MediaItemDetail.model_validate(hydrated or media_item)
            return {"media_item": detail.model_dump(), "source_name": source}

    result = asyncio.run(_run())
    logger.info("Ingested %s from %s", identifier, source)
    return result
