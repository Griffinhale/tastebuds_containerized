from __future__ import annotations

import asyncio
import logging

from app.db.session import async_session
from app.services import media_service

logger = logging.getLogger("app.jobs.preview_cleanup")


def prune_external_search_previews() -> int:
    async def _run() -> int:
        async with async_session() as session:
            deleted = await media_service.prune_external_previews(session)
            return deleted

    deleted_count = asyncio.run(_run())
    logger.info("Pruned %d expired external search previews", deleted_count)
    return deleted_count
