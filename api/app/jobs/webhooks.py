from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.db.session import async_session
from app.services.webhook_service import WebhookEvent, handle_webhook

logger = logging.getLogger("app.jobs.webhooks")


def handle_webhook_event_job(
    *, provider: str, payload: dict[str, Any], event_type: str | None = None, source_ip: str | None = None
) -> dict[str, Any]:
    """RQ-friendly wrapper to process webhook events asynchronously."""

    async def _run() -> dict[str, Any]:
        async with async_session() as session:
            event = WebhookEvent(provider=provider, payload=payload, event_type=event_type, source_ip=source_ip)
            return await handle_webhook(session, event)

    summary = asyncio.run(_run())
    logger.info("Processed webhook event from %s (%s)", provider, event_type or "unspecified")
    return summary
