"""Integration credential rotation job placeholder."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime

from app.db.session import async_session
from app.services import spotify_service

logger = logging.getLogger("app.jobs.credentials")


def rotate_credential_job(*, provider: str, user_id: str, requested_by: str | None = None) -> dict:
    """
    Placeholder credential rotation job to keep the integrations queue alive.

    Concrete connectors (Spotify, Arr, Jellyfin) can plug their refresh logic here.
    """
    async def _run() -> dict:
        async with async_session() as session:
            if provider == "spotify":
                return await spotify_service.rotate_tokens(session, user_id=uuid.UUID(user_id))
            return {
                "status": "unsupported",
                "provider": provider,
                "user_id": user_id,
                "requested_by": requested_by,
                "rotated_at": datetime.utcnow().isoformat() + "Z",
            }

    logger.info(
        "Rotate credential requested for provider=%s user=%s requested_by=%s",
        provider,
        user_id,
        requested_by,
    )
    return asyncio.run(_run())
