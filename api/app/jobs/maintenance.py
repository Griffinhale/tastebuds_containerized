from __future__ import annotations

import asyncio
import logging

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
