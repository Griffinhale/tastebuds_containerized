"""Automation execution engine for rule actions.

Invariants:
- Action configs are validated before execution.
- last_error captures a short failure summary for UI surfaces.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.automation import AutomationRule
from app.services import media_service, sync_service

logger = logging.getLogger("app.services.automation_engine")

ActionHandler = Callable[[AsyncSession, AutomationRule, uuid.UUID | None], Awaitable[dict[str, Any]]]


class AutomationExecutionError(RuntimeError):
    """Raised for validation errors that should be surfaced to the caller."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    now = datetime.utcnow()
    return now if now.tzinfo else now.replace(tzinfo=timezone.utc)


def _truncate_error(value: str | None, limit: int = 500) -> str | None:
    if not value:
        return None
    return value[:limit]


def _coerce_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n"}:
            return False
    return bool(value)


def _normalize_config(config: Any) -> dict[str, Any]:
    if config is None:
        return {}
    if not isinstance(config, dict):
        raise AutomationExecutionError("action_config_invalid")
    return config


async def _execute_ingest_action(
    session: AsyncSession,
    rule: AutomationRule,
    requested_by: uuid.UUID | None,
) -> dict[str, Any]:
    config = _normalize_config(rule.action_config)
    source = _coerce_str(config.get("source") or config.get("provider"))
    identifier = _coerce_str(
        config.get("identifier")
        or config.get("external_id")
        or config.get("source_id")
        or config.get("url")
    )
    if not source or not identifier:
        raise AutomationExecutionError("ingest_missing_source_or_identifier")
    force_refresh = _coerce_bool(config.get("force_refresh"), default=False)
    media_item = await media_service.ingest_from_source(
        session,
        source=source,
        identifier=identifier,
        force_refresh=force_refresh,
    )
    return {
        "status": "ingested",
        "source": source,
        "identifier": identifier,
        "media_item_id": str(media_item.id),
        "force_refresh": force_refresh,
        "requested_by": str(requested_by) if requested_by else None,
    }


async def _execute_sync_action(
    session: AsyncSession,
    rule: AutomationRule,
    requested_by: uuid.UUID | None,
) -> dict[str, Any]:
    config = _normalize_config(rule.action_config)
    provider = _coerce_str(config.get("provider") or config.get("source"))
    external_id = _coerce_str(
        config.get("external_id") or config.get("identifier") or config.get("source_id")
    )
    if not provider:
        raise AutomationExecutionError("sync_missing_provider")
    if not external_id:
        if provider in sync_service.SUPPORTED_SYNC_PROVIDERS:
            external_id = "library"
        else:
            raise AutomationExecutionError("sync_missing_external_id")
    action = _coerce_str(config.get("action")) or "sync"
    force_refresh = _coerce_bool(config.get("force_refresh"), default=False)
    task = sync_service.SyncTask(
        provider=provider,
        external_id=external_id,
        action=action,
        force_refresh=force_refresh,
        requested_by=requested_by,
    )
    return await sync_service.process_sync_task(session, task)


ACTION_HANDLERS: dict[str, ActionHandler] = {
    "ingest": _execute_ingest_action,
    "sync": _execute_sync_action,
}


async def execute_rule(
    session: AsyncSession,
    *,
    rule: AutomationRule,
    requested_by: uuid.UUID | None,
    allow_disabled: bool = False,
) -> dict[str, Any]:
    """Execute a rule action and record the outcome."""
    ran_at = _utcnow()
    status = "completed"
    error: str | None = None
    detail: dict[str, Any] = {"action_type": rule.action_type}

    if not allow_disabled and not rule.enabled:
        status = "skipped"
        detail["reason"] = "rule_disabled"
    else:
        handler = ACTION_HANDLERS.get(rule.action_type)
        if not handler:
            status = "failed"
            error = f"unsupported_action:{rule.action_type}"
            detail["error"] = error
        else:
            try:
                action_result = await handler(session, rule, requested_by)
                detail["action_result"] = action_result
                if isinstance(action_result, dict):
                    action_status = action_result.get("status")
                    if action_status:
                        detail["action_status"] = action_status
                        if action_status in {"failed", "skipped"}:
                            status = action_status
                            if action_status == "failed" and not error:
                                action_error = action_result.get("error")
                                error = str(action_error) if action_error else "action_failed"
                                detail["error"] = error
            except AutomationExecutionError as exc:
                status = "failed"
                error = exc.message
                detail["error"] = error
            except HTTPException as exc:
                status = "failed"
                error = str(exc.detail)
                detail["error"] = error
            except Exception as exc:
                logger.exception("Automation execution failed for %s", rule.id)
                status = "failed"
                error = str(exc)
                detail["error"] = error

    rule.last_run_at = ran_at
    rule.last_error = _truncate_error(error)
    await session.commit()
    return {"status": status, "ran_at": ran_at, "detail": detail}


async def execute_rule_by_id(
    session: AsyncSession,
    *,
    rule_id: uuid.UUID,
    requested_by: uuid.UUID | None,
    allow_disabled: bool = False,
) -> dict[str, Any]:
    """Execute a rule by ID for worker-driven runs."""
    if not isinstance(rule_id, uuid.UUID):
        rule_id = uuid.UUID(str(rule_id))
    rule = await session.get(AutomationRule, rule_id)
    if not rule:
        return {
            "status": "failed",
            "ran_at": _utcnow(),
            "detail": {"error": "rule_not_found"},
        }
    if requested_by and rule.user_id != requested_by:
        return {
            "status": "failed",
            "ran_at": _utcnow(),
            "detail": {"error": "rule_owner_mismatch"},
        }
    return await execute_rule(
        session,
        rule=rule,
        requested_by=requested_by,
        allow_disabled=allow_disabled,
    )
