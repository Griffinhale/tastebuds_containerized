from __future__ import annotations

import logging
from datetime import datetime, timedelta

from rq_scheduler import Scheduler

from app.core.config import settings
from app.jobs.maintenance import prune_external_search_previews_job, prune_ingestion_payloads_job
from app.services.task_queue import task_queue

logger = logging.getLogger("app.jobs.schedule_registry")


def _schedule_entries() -> list[dict]:
    preview_interval = max(60, settings.external_search_preview_ttl_seconds // 2)
    queue_name = task_queue.queue_names[0] if task_queue.queue_names else "default"
    entries: list[dict] = [
        {
            "id": "maintenance:prune_external_previews",
            "func": prune_external_search_previews_job,
            "interval": preview_interval,
            "repeat": None,
            "queue_name": "maintenance" if "maintenance" in task_queue.queue_names else queue_name,
        },
    ]
    if settings.ingestion_payload_retention_days > 0:
        payload_interval = max(3600, settings.ingestion_payload_retention_days * 86400 // 2)
        entries.append(
            {
                "id": "maintenance:prune_ingestion_payloads",
                "func": prune_ingestion_payloads_job,
                "interval": payload_interval,
                "repeat": None,
                "queue_name": "maintenance" if "maintenance" in task_queue.queue_names else queue_name,
            }
        )
    return entries


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
