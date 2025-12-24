from __future__ import annotations

import logging
from redis import Redis
from rq import Connection, Queue, Worker

from app.core.config import settings

WORKER_LOG_FORMAT = "%(asctime)s %(name)s [%(levelname)s] %(message)s"


def _configure_logging() -> None:
    logging.basicConfig(level=settings.log_level, format=WORKER_LOG_FORMAT, force=True)


def _queue_objects(connection: Redis) -> list[Queue]:
    return [Queue(name, connection=connection) for name in settings.worker_queue_names]


def main() -> None:
    _configure_logging()
    logger = logging.getLogger("app.worker")
    redis_connection = Redis.from_url(settings.redis_url)
    queues = _queue_objects(redis_connection)
    if not queues:
        logger.error("No worker queues configured; set WORKER_QUEUE_NAMES or rely on the default.")
        return
    logger.info("Starting worker for queues: %s", ", ".join(settings.worker_queue_names))
    with Connection(redis_connection):
        worker = Worker(queues, connection=redis_connection, name="tastebuds-worker")
        try:
            worker.work(with_scheduler=True)
        except KeyboardInterrupt:
            worker.request_stop()
            logger.info("Worker shutdown requested")


if __name__ == "__main__":
    main()
