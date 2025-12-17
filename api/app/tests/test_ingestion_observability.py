from __future__ import annotations

import asyncio

import pytest

from app.ingestion.http import ExternalAPIError
from app.ingestion.observability import CircuitOpenError, IngestionMonitor


@pytest.mark.asyncio
async def test_ingestion_monitor_opens_circuit_after_repeated_failures() -> None:
    monitor = IngestionMonitor(circuit_threshold=2, base_backoff_seconds=0.01, max_backoff_seconds=0.02)

    async def failing_call() -> None:
        raise ExternalAPIError("boom")

    with pytest.raises(ExternalAPIError):
        await monitor.track("tmdb", "fetch", failing_call)
    with pytest.raises(ExternalAPIError):
        await monitor.track("tmdb", "fetch", failing_call)

    assert monitor.allow_call("tmdb") is False
    with pytest.raises(CircuitOpenError):
        await monitor.track("tmdb", "fetch", failing_call)

    snapshot = await monitor.snapshot()
    assert snapshot["tmdb"]["circuit"]["opened_count"] >= 1
    assert snapshot["tmdb"]["operations"]["fetch"]["failed"] == 2

    await monitor.record_skip("tmdb", "fetch", reason="circuit_open", context={"identifier": "123"})
    updated = await monitor.snapshot()
    assert updated["tmdb"]["operations"]["fetch"]["skipped"] >= 1


@pytest.mark.asyncio
async def test_ingestion_monitor_recovers_after_cooldown_and_success() -> None:
    monitor = IngestionMonitor(circuit_threshold=1, base_backoff_seconds=0.01, max_backoff_seconds=0.02)

    async def failing_call() -> None:
        raise ExternalAPIError("boom")

    with pytest.raises(ExternalAPIError):
        await monitor.track("lastfm", "fetch", failing_call)

    assert monitor.allow_call("lastfm") is False
    await asyncio.sleep(0.02)

    async def ok_call() -> str:
        return "ok"

    assert await monitor.track("lastfm", "fetch", ok_call, context={"identifier": "abc"}) == "ok"
    snapshot = await monitor.snapshot()
    assert snapshot["lastfm"]["operations"]["fetch"]["succeeded"] == 1
    assert snapshot["lastfm"]["circuit"]["failure_streak"] == 0
