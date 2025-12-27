"""Maintenance jobs for preview and payload retention."""

from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.db.session import async_session
from app.services import media_service

logger = logging.getLogger("app.jobs.maintenance")


def prune_external_search_previews_job() -> dict[str, int]:
    """Scheduled cleanup for short-lived external search previews."""

    async def _run() -> int:
        async with async_session() as session:
            return await media_service.prune_external_previews(session)

    deleted = asyncio.run(_run())
    logger.info("Pruned %d expired external search previews", deleted)
    return {"deleted": deleted}


def prune_ingestion_payloads_job(retention_days: int | None = None) -> dict[str, int]:
    """Scheduled cleanup for long-lived raw ingestion payloads."""

    async def _run() -> int:
        async with async_session() as session:
            return await media_service.prune_media_source_payloads(
                session, retention_days=retention_days or settings.ingestion_payload_retention_days
            )

    stripped = asyncio.run(_run())
    logger.info(
        "Scrubbed %d ingestion payloads older than %s days",
        stripped,
        retention_days or settings.ingestion_payload_retention_days,
    )
    return {"stripped": stripped}
