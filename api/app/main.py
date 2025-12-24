from typing import Any

from fastapi import Depends, FastAPI
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


@app.get("/health", tags=["internal"])
@app.get(f"{settings.api_prefix}/health", tags=["internal"])
async def health(current_user: User | None = Depends(get_optional_current_user)) -> dict[str, Any]:
    snapshot = await ingestion_monitor.snapshot()
    telemetry = _summarize_ingestion(snapshot)
    status = "ok" if not telemetry["issues"] else "degraded"
    result = {"status": status}
    if current_user:
        result["ingestion"] = telemetry
    return result
