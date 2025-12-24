import ipaddress
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import get_optional_current_user
from app.api.router import api_router
from app.core.config import settings
from app.ingestion.observability import ingestion_monitor
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


def _summarize_ingestion(snapshot: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    for source, payload in snapshot.items():
        circuit = payload.get("circuit", {})
        remaining = float(circuit.get("remaining_cooldown") or 0.0)
        if remaining > 0:
            issues.append(
                {
                    "source": source,
                    "reason": "circuit_open",
                    "remaining_cooldown": round(remaining, 2),
                }
            )
        operations = payload.get("operations", {})
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
    return {"sources": snapshot, "issues": issues}


def _entry_matches(entry: str, candidate: str) -> bool:
    try:
        network = ipaddress.ip_network(entry, strict=False)
        return ipaddress.ip_address(candidate) in network
    except ValueError:
        return entry.casefold() == candidate.casefold()


def _ip_or_host_allowlisted(request: Request) -> bool:
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
    if current_user:
        return True
    return _ip_or_host_allowlisted(request)


@app.get("/health", tags=["internal"])
@app.get(f"{settings.api_prefix}/health", tags=["internal"])
async def health(request: Request, current_user: User | None = Depends(get_optional_current_user)) -> dict[str, Any]:
    if not _can_view_health_detail(request, current_user):
        return {"status": "ok"}

    snapshot = await ingestion_monitor.snapshot()
    telemetry = _summarize_ingestion(snapshot)
    status = "ok" if not telemetry["issues"] else "degraded"
    return {"status": status, "ingestion": telemetry}
