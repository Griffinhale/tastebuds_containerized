"""Ensure log redaction prevents secret leakage."""

from __future__ import annotations

import logging

from redis.exceptions import RedisError

import app.services.task_queue as task_queue_module
from app.core.config import settings


def test_task_queue_redacts_redis_url_in_logs(monkeypatch, caplog):
    secret_url = "redis://:supersecret@localhost:6379/0"
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "redis_url", secret_url)

    class DummyRedis:
        @staticmethod
        def from_url(url: str):
            raise RedisError(f"Connection failed: {url}")

    monkeypatch.setattr(task_queue_module, "Redis", DummyRedis)

    caplog.set_level(logging.WARNING, logger="app.services.task_queue")
    task_queue_module.TaskQueue()

    assert "supersecret" not in caplog.text
    assert "redis://***@localhost:6379/0" in caplog.text
