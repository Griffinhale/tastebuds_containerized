"""FastAPI application entrypoint and health reporting utilities.

Invariants:
- Health detail is only exposed to authenticated users or allowlisted hosts.
"""

import ipaddress
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import get_optional_current_user
from app.api.router import api_router
from app.core.config import settings
from app.ingestion.observability import ingestion_monitor
from app.jobs.schedule_registry import ensure_schedules
from app.models.user import User

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_prefix)


@app.on_event("startup")
async def _register_schedules() -> None:
    """Register scheduled jobs on startup."""
    ensure_schedules()


def _summarize_ingestion(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Condense ingestion monitor state into health-friendly telemetry.

    Implementation notes:
    - Treat open circuits and repeated failures as degraded signals.
    - Preserve per-operation errors to aid ops troubleshooting.
    """
    issues: list[dict[str, Any]] = []
    sources: dict[str, Any] = {}
    for source, payload in snapshot.items():
        circuit = payload.get("circuit", {})
        remaining = float(circuit.get("remaining_cooldown") or 0.0)
        state = "ok"
        circuit_open = False
        if remaining > 0:
            issues.append(
                {
                    "source": source,
                    "reason": "circuit_open",
                    "remaining_cooldown": round(remaining, 2),
                }
            )
            state = "degraded"
            circuit_open = True
        operations = payload.get("operations", {})
        failure_total = 0
        repeated_failure: dict[str, Any] | None = None
        last_error: str | None = None
        for operation, metrics in operations.items():
            last_error = metrics.get("last_error")
            if last_error:
                issues.append(
                    {
                        "source": source,
                        "operation": operation,
                        "reason": "last_error",
                        "error": last_error,
                    }
                )
            failed_count = int(metrics.get("failed") or 0)
            failure_total += failed_count
            if failed_count >= 3:
                repeated_failure = {"operation": operation, "failed": failed_count}
        if repeated_failure:
            issues.append(
                {
                    "source": source,
                    "reason": "repeated_failures",
                    "operation": repeated_failure["operation"],
                    "failed": repeated_failure["failed"],
                }
            )
            state = "degraded"
        elif last_error and state != "circuit_open":
            state = "degraded"
        sources[source] = {
            "state": state,
            "circuit_open": circuit_open,
            "circuit": circuit,
            "operations": operations,
            "failure_total": failure_total,
            "last_error": last_error,
            "repeated_failure": repeated_failure,
        }
    return {"sources": sources, "issues": issues}


def _entry_matches(entry: str, candidate: str) -> bool:
    """Return True if an allowlist entry matches a candidate host/IP."""
    try:
        network = ipaddress.ip_network(entry, strict=False)
        return ipaddress.ip_address(candidate) in network
    except ValueError:
        return entry.casefold() == candidate.casefold()


def _ip_or_host_allowlisted(request: Request) -> bool:
    """Check request client/host headers against the health allowlist."""
    if not settings.health_allowlist:
        return False
    client_candidates: list[str] = []
    if request.client and request.client.host:
        client_candidates.append(request.client.host)
    host_header = request.headers.get("host")
    if host_header:
        client_candidates.append(host_header.split(":")[0])
    for candidate in client_candidates:
        for entry in settings.health_allowlist:
            if entry and _entry_matches(entry, candidate):
                return True
    return False


def _can_view_health_detail(request: Request, current_user: User | None) -> bool:
    """Authorize access to detailed health telemetry."""
    if current_user:
        return True
    return _ip_or_host_allowlisted(request)


@app.get("/health", tags=["internal"])
@app.get(f"{settings.api_prefix}/health", tags=["internal"])
async def health(request: Request, current_user: User | None = Depends(get_optional_current_user)) -> dict[str, Any]:
    """Return health status and optionally include ingestion telemetry."""
    if not _can_view_health_detail(request, current_user):
        return {"status": "ok"}

    snapshot = await ingestion_monitor.snapshot()
    telemetry = _summarize_ingestion(snapshot)
    status = "ok" if not telemetry["issues"] else "degraded"
    return {"status": status, "ingestion": telemetry}
