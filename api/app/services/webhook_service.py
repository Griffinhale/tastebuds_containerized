"""Webhook normalization helpers for integrations."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("app.services.webhooks")


@dataclass(slots=True)
class WebhookEvent:
    """Normalized webhook payload passed into handlers."""
    provider: str
    payload: dict[str, Any] = field(default_factory=dict)
    event_type: str | None = None
    source_ip: str | None = None
    user_id: uuid.UUID | None = None
    received_at: datetime = field(default_factory=datetime.utcnow)


async def handle_webhook(session: AsyncSession, event: WebhookEvent) -> dict[str, Any]:
    """Normalize webhook payloads and enqueue integration ingestion."""
    payload_bytes = len(json.dumps(event.payload, default=str).encode("utf-8"))
    summary = {
        "provider": event.provider,
        "event_type": event.event_type,
        "source_ip": event.source_ip,
        "payload_bytes": payload_bytes,
        "received_at": event.received_at.isoformat() + "Z",
    }
    logger.info(
        "Webhook received from %s (%s) [bytes=%s, source_ip=%s]",
        event.provider,
        event.event_type or "unspecified",
        payload_bytes,
        event.source_ip or "unknown",
    )
    if event.provider == "arr" and event.user_id:
        from app.services.integration_queue_service import record_arr_event

        ingest_event = await record_arr_event(
            session,
            user_id=event.user_id,
            provider=event.provider,
            payload=event.payload,
        )
        summary["ingest_event_id"] = str(ingest_event.id)
        summary["ingest_status"] = ingest_event.status.value
    return summary
