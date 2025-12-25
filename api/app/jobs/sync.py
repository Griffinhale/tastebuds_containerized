from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from app.db.session import async_session
from app.services.sync_service import SyncTask, process_sync_task

logger = logging.getLogger("app.jobs.sync")


def run_sync_job(
    *,
    provider: str,
    external_id: str,
    action: str = "ingest",
    force_refresh: bool = False,
    requested_by: str | None = None,
) -> dict[str, Any]:
    """RQ-friendly sync/refresh hook."""

    async def _run() -> dict[str, Any]:
        async with async_session() as session:
            requester = uuid.UUID(requested_by) if requested_by else None
            task = SyncTask(
                provider=provider,
                external_id=external_id,
                action=action,
                force_refresh=force_refresh,
                requested_by=requester,
            )
            return await process_sync_task(session, task)

    summary = asyncio.run(_run())
    logger.info("Sync job complete for %s (%s)", external_id, provider)
    return summary
