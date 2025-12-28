"""Placeholder sync handlers for integration providers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.services.sync_service import SyncTask

logger = logging.getLogger("app.services.integration_sync")

SUPPORTED_SYNC_PROVIDERS = {"jellyfin", "plex"}


async def process_integration_sync(session: AsyncSession, task: "SyncTask") -> dict[str, Any]:
    """Handle integration sync tasks for non-ingestion providers."""
    _ = session
    logger.info("Integration sync placeholder for %s (%s)", task.provider, task.action)
    return {
        "status": "pending",
        "provider": task.provider,
        "external_id": task.external_id,
        "action": task.action,
        "force_refresh": task.force_refresh,
        "requested_by": str(task.requested_by) if task.requested_by else None,
        "requested_at": task.requested_at.isoformat() + "Z",
    }
