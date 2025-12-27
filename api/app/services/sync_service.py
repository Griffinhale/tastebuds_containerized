"""Sync workflow helpers for background ingestion tasks."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import media_service

logger = logging.getLogger("app.services.sync")


@dataclass(slots=True)
class SyncTask:
    """Structured payload describing a sync request."""
    provider: str
    external_id: str
    action: str = "ingest"
    force_refresh: bool = False
    requested_by: uuid.UUID | None = None
    requested_at: datetime = field(default_factory=datetime.utcnow)


async def process_sync_task(session: AsyncSession, task: SyncTask) -> dict[str, Any]:
    """Execute sync tasks (ingest/refresh) through the worker queue."""
    if task.action == "ingest":
        media_item = await media_service.ingest_from_source(
            session,
            source=task.provider,
            identifier=task.external_id,
            force_refresh=task.force_refresh,
        )
        logger.info(
            "Synced %s from %s (force_refresh=%s)",
            task.external_id,
            task.provider,
            task.force_refresh,
        )
        return {
            "status": "ingested",
            "provider": task.provider,
            "external_id": task.external_id,
            "media_item_id": str(media_item.id),
            "force_refresh": task.force_refresh,
            "requested_by": str(task.requested_by) if task.requested_by else None,
            "requested_at": task.requested_at.isoformat() + "Z",
        }

    logger.info(
        "Sync task skipped for %s (provider=%s action=%s)", task.external_id, task.provider, task.action
    )
    return {
        "status": "skipped",
        "provider": task.provider,
        "external_id": task.external_id,
        "action": task.action,
    }
