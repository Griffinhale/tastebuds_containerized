"""Worker job entrypoint for automation rule execution."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from app.db.session import async_session
from app.services import automation_engine

logger = logging.getLogger("app.jobs.automations")


def run_automation_rule_job(
    *,
    rule_id: str,
    requested_by: str | None = None,
    allow_disabled: bool = False,
) -> dict[str, Any]:
    """Execute an automation rule within a worker context."""

    async def _run() -> dict[str, Any]:
        async with async_session() as session:
            requester = uuid.UUID(requested_by) if requested_by else None
            return await automation_engine.execute_rule_by_id(
                session,
                rule_id=uuid.UUID(rule_id),
                requested_by=requester,
                allow_disabled=allow_disabled,
            )

    result = asyncio.run(_run())
    logger.info("Automation run complete for %s (%s)", rule_id, result.get("status"))
    return result
