from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger("app.jobs.credentials")


def rotate_credential_job(*, provider: str, user_id: str, requested_by: str | None = None) -> dict:
    """
    Placeholder credential rotation job to keep the integrations queue alive.

    Concrete connectors (Spotify, Arr, Jellyfin) can plug their refresh logic here.
    """
    logger.info("Rotate credential requested for provider=%s user=%s requested_by=%s", provider, user_id, requested_by)
    return {"provider": provider, "user_id": user_id, "requested_by": requested_by, "rotated_at": datetime.utcnow().isoformat() + "Z"}
