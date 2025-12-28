"""Availability refresh jobs."""

from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.db.session import async_session
from app.services import availability_service

logger = logging.getLogger("app.jobs.availability")


def refresh_availability_job(stale_days: int | None = None) -> dict[str, int]:
    """Mark stale availability entries as unknown."""

    async def _run() -> int:
        async with async_session() as session:
            return await availability_service.refresh_stale_availability(
                session, stale_days=stale_days or settings.availability_refresh_days
            )

    refreshed = asyncio.run(_run())
    logger.info("Refreshed availability entries marked stale: %d", refreshed)
    return {"refreshed": refreshed}
