from __future__ import annotations

import logging
from datetime import datetime, timedelta

from rq_scheduler import Scheduler

from app.core.config import settings
from app.jobs.maintenance import prune_external_search_previews_job
from app.services.task_queue import task_queue

logger = logging.getLogger("app.jobs.schedule_registry")


def _schedule_entries() -> list[dict]:
    preview_interval = max(60, settings.external_search_preview_ttl_seconds // 2)
    queue_name = task_queue.queue_names[0] if task_queue.queue_names else "default"
    return [
        {
            "id": "maintenance:prune_external_previews",
            "func": prune_external_search_previews_job,
            "interval": preview_interval,
            "repeat": None,
            "queue_name": queue_name,
        }
    ]


def ensure_schedules() -> None:
    """Idempotently register periodic jobs with rq-scheduler."""
    if settings.environment.lower() == "test":
        return
    if not task_queue.connection:
        logger.info("Skipping scheduler bootstrap; queue connection is unavailable")
        return
    scheduler = Scheduler(connection=task_queue.connection, queue_name=task_queue.queue_names[0])
    for entry in _schedule_entries():
        existing = scheduler.get_job(entry["id"])
        if existing:
            continue
        scheduler.schedule(
            scheduled_time=datetime.utcnow(),
            func=entry["func"],
            interval=entry["interval"],
            repeat=entry["repeat"],
            id=entry["id"],
            queue_name=entry["queue_name"],
            result_ttl=int(timedelta(hours=1).total_seconds()),
        )
        logger.info("Scheduled job %s every %ss on queue %s", entry["id"], entry["interval"], entry["queue_name"])
