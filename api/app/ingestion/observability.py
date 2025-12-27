"""Circuit breaker and metrics tracking for ingestion connectors."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, DefaultDict

logger = logging.getLogger("app.ingestion")


class CircuitOpenError(Exception):
    """Raised when a source circuit is open and calls are temporarily blocked."""


@dataclass
class CircuitBreakerState:
    """Track per-source failure streaks and cooldown windows."""
    threshold: int = 3
    base_backoff_seconds: float = 15.0
    max_backoff_seconds: float = 300.0
    failure_streak: int = 0
    open_until: float = 0.0
    current_backoff: float = field(init=False)
    opened_count: int = 0

    def __post_init__(self) -> None:
        """Initialize the current backoff based on base settings."""
        self.current_backoff = self.base_backoff_seconds

    def can_call(self) -> bool:
        """Return True if the circuit is closed and calls are allowed."""
        return time.monotonic() >= self.open_until

    def remaining_cooldown(self) -> float:
        """Return remaining cooldown seconds before calls are allowed."""
        if self.can_call():
            return 0.0
        return self.open_until - time.monotonic()

    def record_success(self) -> None:
        """Reset circuit state after a successful call."""
        self.failure_streak = 0
        self.open_until = 0.0
        self.current_backoff = self.base_backoff_seconds

    def record_failure(self) -> None:
        """Advance circuit state and open on threshold breaches."""
        self.failure_streak += 1
        if self.failure_streak < self.threshold:
            return
        now = time.monotonic()
        self.open_until = now + self.current_backoff
        self.failure_streak = 0
        self.opened_count += 1
        self.current_backoff = min(self.current_backoff * 2, self.max_backoff_seconds)

    def snapshot(self) -> dict[str, Any]:
        """Return a serializable snapshot of the circuit state."""
        return {
            "failure_streak": self.failure_streak,
            "open_until": self.open_until,
            "remaining_cooldown": self.remaining_cooldown(),
            "current_backoff": self.current_backoff,
            "opened_count": self.opened_count,
        }


@dataclass
class OperationMetrics:
    """Aggregated counters for a source operation."""
    started: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    last_latency_ms: float | None = None
    last_error: str | None = None


class IngestionMonitor:
    """Track ingestion performance and enforce circuit breaking."""
    def __init__(
        self,
        *,
        circuit_threshold: int = 3,
        base_backoff_seconds: float = 15.0,
        max_backoff_seconds: float = 300.0,
    ) -> None:
        self._metrics: DefaultDict[str, DefaultDict[str, OperationMetrics]] = defaultdict(
            lambda: defaultdict(OperationMetrics)
        )
        self._circuits: DefaultDict[str, CircuitBreakerState] = defaultdict(
            lambda: CircuitBreakerState(
                threshold=circuit_threshold,
                base_backoff_seconds=base_backoff_seconds,
                max_backoff_seconds=max_backoff_seconds,
            )
        )
        self._lock = asyncio.Lock()

    def allow_call(self, source: str) -> bool:
        """Return True if a source circuit allows new work."""
        circuit = self._circuits[source]
        return circuit.can_call()

    async def record_skip(
        self,
        source: str,
        operation: str,
        *,
        reason: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Log a skipped call with circuit state for observability."""
        async with self._lock:
            metrics = self._metrics[source][operation]
            metrics.skipped += 1
            payload = {
                "event": "ingestion_skip",
                "source": source,
                "operation": operation,
                "reason": reason,
                "context": context or {},
                "circuit": self._circuits[source].snapshot(),
            }
        logger.warning(json.dumps(payload))

    async def track(
        self,
        source: str,
        operation: str,
        func: Callable[[], Awaitable[Any]],
        *,
        context: dict[str, Any] | None = None,
    ) -> Any:
        """Execute a connector call while tracking metrics and circuit state.

        Implementation notes:
        - Failures update the circuit breaker and emit structured logs.
        - Successes reset the failure streak and record latency.
        """
        context = context or {}
        async with self._lock:
            circuit = self._circuits[source]
            if not circuit.can_call():
                remaining = circuit.remaining_cooldown()
                metrics = self._metrics[source][operation]
                metrics.skipped += 1
                payload = {
                    "event": "ingestion_circuit_open",
                    "source": source,
                    "operation": operation,
                    "context": context,
                    "remaining_cooldown": remaining,
                }
                logger.warning(json.dumps(payload))
                raise CircuitOpenError(f"{source} circuit open for {remaining:.2f}s")
            metrics = self._metrics[source][operation]
            metrics.started += 1

        start = time.monotonic()
        try:
            result = await func()
        except Exception as exc:  # noqa: BLE001
            latency_ms = (time.monotonic() - start) * 1000
            async with self._lock:
                metrics = self._metrics[source][operation]
                metrics.failed += 1
                metrics.last_latency_ms = latency_ms
                metrics.last_error = str(exc)
                self._circuits[source].record_failure()
                payload = {
                    "event": "ingestion_failure",
                    "source": source,
                    "operation": operation,
                    "error": str(exc),
                    "latency_ms": round(latency_ms, 2),
                    "context": context,
                    "circuit": self._circuits[source].snapshot(),
                }
            logger.warning(json.dumps(payload))
            raise

        latency_ms = (time.monotonic() - start) * 1000
        async with self._lock:
            metrics = self._metrics[source][operation]
            metrics.succeeded += 1
            metrics.last_latency_ms = latency_ms
            metrics.last_error = None
            self._circuits[source].record_success()
            payload = {
                "event": "ingestion_success",
                "source": source,
                "operation": operation,
                "latency_ms": round(latency_ms, 2),
                "context": context,
                "circuit": self._circuits[source].snapshot(),
            }
        logger.info(json.dumps(payload))
        return result

    async def snapshot(self) -> dict[str, Any]:
        """Return a snapshot of all tracked source metrics."""
        async with self._lock:
            snap: dict[str, Any] = {}
            for source, operations in self._metrics.items():
                snap[source] = {
                    "circuit": self._circuits[source].snapshot(),
                    "operations": {
                        name: {
                            "started": metrics.started,
                            "succeeded": metrics.succeeded,
                            "failed": metrics.failed,
                            "skipped": metrics.skipped,
                            "last_latency_ms": metrics.last_latency_ms,
                            "last_error": metrics.last_error,
                        }
                        for name, metrics in operations.items()
                    },
                }
            return snap


ingestion_monitor = IngestionMonitor()
