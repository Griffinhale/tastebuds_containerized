from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import require_ops_admin
from app.models.user import User
from app.services.task_queue import task_queue

router = APIRouter()


@router.get("/queues", tags=["ops"])
async def queue_health(_: User = Depends(require_ops_admin)) -> dict:
    """
    Minimal operations dashboard for Redis/RQ health.

    Requires authentication to avoid leaking operational data to anonymous callers.
    """

    return task_queue.snapshot()
