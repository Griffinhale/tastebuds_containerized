"""RQ task queue wrapper with inline fallback for local/test runs."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Callable

from redis import Redis
from redis.exceptions import RedisError
from rq import Queue

try:  # RQ < 1.10 lacks Retry; fallback gracefully
    from rq.retry import Retry  # type: ignore
except Exception:  # pragma: no cover - runtime compatibility
    Retry = None  # type: ignore
from rq.registry import DeferredJobRegistry, FailedJobRegistry, ScheduledJobRegistry, StartedJobRegistry
from rq.worker import Worker
from rq_scheduler import Scheduler

from app.core.config import settings
from app.services.credential_vault import credential_vault

logger = logging.getLogger("app.services.task_queue")

# Retry profile that gives connectors a few chances with backoff.
DEFAULT_RETRY = Retry(max=3, interval=[5, 15, 30]) if Retry else None


def _maybe_async(value: Any) -> Any:
    """Normalize callables/coroutines into an awaitable result."""
    if asyncio.iscoroutine(value):
        return value
    if callable(value):
        result = value()
        if asyncio.iscoroutine(result):
            return result
        return result
    return value


class TaskQueue:
    """Thin wrapper around RQ that can fall back to inline execution."""

    def __init__(self) -> None:
        self.queue_names: list[str] = settings.worker_queue_names or ["default"]
        self._connection: Redis | None = None
        self._enabled = False
        self._supports_retry = Retry is not None
        self._bootstrap()

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def connection(self) -> Redis | None:
        return self._connection

    def _bootstrap(self) -> None:
        """Initialize Redis connectivity unless disabled for tests."""
        if settings.environment.lower() == "test":
            logger.info("Task queue disabled in test environment")
            return
        try:
            connection = Redis.from_url(settings.redis_url)
            connection.ping()
        except Exception as exc:  # pragma: no cover - network/redis specific
            logger.warning("Redis unavailable; running jobs inline: %s", exc)
            self._connection = None
            self._enabled = False
            return
        self._connection = connection
        self._enabled = True
        logger.info("Task queue ready (queues: %s)", ", ".join(self.queue_names))

    def get_queue(self, queue_name: str | None = None) -> Queue:
        """Return a configured queue instance for enqueuing jobs."""
        if not self._connection:
            raise RuntimeError("Queue connection not initialized")
        target = queue_name or (self.queue_names[0] if self.queue_names else "default")
        return Queue(target, connection=self._connection)

    async def enqueue_webhook_event(
        self,
        *,
        provider: str,
        payload: dict[str, Any],
        event_type: str | None = None,
        source_ip: str | None = None,
        user_id: str | None = None,
    ) -> Any:
        """Dispatch webhook events through the dedicated queue."""
        from app.jobs.webhooks import handle_webhook_event_job

        return await self.enqueue_or_run(
            handle_webhook_event_job,
            queue_name="webhooks",
            timeout_seconds=30,
            description=f"webhook:{provider}",
            provider=provider,
            payload=payload,
            event_type=event_type,
            source_ip=source_ip,
            user_id=user_id,
        )

    async def enqueue_sync_task(
        self,
        *,
        provider: str,
        external_id: str,
        action: str = "ingest",
        force_refresh: bool = False,
        requested_by: str | None = None,
    ) -> Any:
        """Dispatch sync/refresh work through the worker queue."""
        from app.jobs.sync import run_sync_job

        return await self.enqueue_or_run(
            run_sync_job,
            queue_name="sync",
            timeout_seconds=120,
            description=f"sync:{provider}:{external_id}",
            provider=provider,
            external_id=external_id,
            action=action,
            force_refresh=force_refresh,
            requested_by=requested_by,
        )

    async def enqueue_credential_rotation(
        self, *, provider: str, user_id: uuid.UUID, requested_by: str | None = None
    ) -> Any:
        """Dedicated pipeline for rotating third-party credentials."""
        from app.jobs.credentials import rotate_credential_job

        return await self.enqueue_or_run(
            rotate_credential_job,
            queue_name="integrations",
            timeout_seconds=30,
            description=f"rotate:{provider}:{user_id}",
            provider=provider,
            user_id=str(user_id),
            requested_by=requested_by,
        )

    async def enqueue_or_run(
        self,
        func: Callable[..., Any],
        *,
        fallback: Callable[[], Any] | None = None,
        queue_name: str | None = None,
        timeout_seconds: int = 60,
        retry: Retry | None = DEFAULT_RETRY,
        description: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Enqueue a job and wait for the result; fall back to inline execution if needed."""

        async def _run_fallback() -> Any:
            target = fallback or (lambda: func(**kwargs))
            result = _maybe_async(target)
            if asyncio.iscoroutine(result):
                return await result
            return result

        if not self._enabled or not self._connection:
            return await _run_fallback()

        def _enqueue_and_wait() -> Any:
            queue = self.get_queue(queue_name)
            enqueue_kwargs: dict[str, Any] = {
                "kwargs": kwargs,
                "job_timeout": timeout_seconds,
                "description": description,
            }
            if retry and self._supports_retry:
                enqueue_kwargs["retry"] = retry
            job = queue.enqueue(func, **enqueue_kwargs)
            return job.wait(timeout=timeout_seconds)

        try:
            return await asyncio.to_thread(_enqueue_and_wait)
        except Exception as exc:  # pragma: no cover - network/redis specific
            logger.warning("Falling back to inline execution after queue failure: %s", exc)
            return await _run_fallback()

    def snapshot(self) -> dict[str, Any]:
        """Return a diagnostic snapshot of queue, worker, and scheduler state."""
        if not self._connection:
            return {
                "status": "offline",
                "queues": [],
                "workers": [],
                "error": "queue connection not initialized",
                "redis_url": settings.redis_url,
                "vault": credential_vault.health(),
            }

        queues: list[dict[str, Any]] = []
        for name in self.queue_names:
            queue = Queue(name, connection=self._connection)
            queues.append(
                {
                    "name": name,
                    "size": queue.count,
                    "deferred": len(DeferredJobRegistry(queue=queue)),
                    "scheduled": len(ScheduledJobRegistry(queue=queue)),
                    "started": len(StartedJobRegistry(queue=queue)),
                    "failed": len(FailedJobRegistry(queue=queue)),
                }
            )

        workers: list[dict[str, Any]] = []
        try:
            for worker in Worker.all(connection=self._connection):
                workers.append(
                    {
                        "name": worker.name,
                        "state": getattr(worker, "state", "unknown"),
                        "queues": list(worker.queue_names()),
                        "current_job_id": worker.get_current_job_id(),
                    }
                )
        except RedisError as exc:  # pragma: no cover - network/redis specific
            logger.warning("Unable to list workers: %s", exc)

        redis_info: dict[str, Any] = {"url": settings.redis_url}
        try:
            redis_info["info"] = self._connection.info(section="server")
        except Exception:  # pragma: no cover - redis specific
            redis_info["info"] = None

        scheduler_summary: dict[str, Any] = {}
        try:
            scheduler = Scheduler(connection=self._connection, queue_name=self.queue_names[0])
            scheduler_summary["scheduled_jobs"] = len(scheduler.get_jobs())
            scheduler_summary["healthy"] = True
        except Exception:  # pragma: no cover - redis specific
            scheduler_summary["scheduled_jobs"] = None
            scheduler_summary["healthy"] = False

        warnings: list[str] = []
        if not workers:
            warnings.append("no_workers")
        if scheduler_summary.get("healthy") is False:
            warnings.append("scheduler_unreachable")
        status = "online" if not warnings else "degraded"
        return {
            "status": status,
            "queues": queues,
            "workers": workers,
            "redis": redis_info,
            "scheduler": scheduler_summary,
            "warnings": warnings,
            "checked_at": datetime.utcnow().isoformat() + "Z",
            "vault": credential_vault.health(),
        }


task_queue = TaskQueue()
