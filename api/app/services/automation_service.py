"""Automation rule storage and execution helpers."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.automations import run_automation_rule_job
from app.models.automation import AutomationRule
from app.schema.automation import AutomationRuleCreate, AutomationRuleUpdate
from app.services import automation_engine
from app.services.task_queue import task_queue


async def list_rules(session: AsyncSession, *, user_id: uuid.UUID) -> list[AutomationRule]:
    """List automation rules for a user."""
    result = await session.execute(select(AutomationRule).where(AutomationRule.user_id == user_id))
    return result.scalars().all()


async def get_rule(session: AsyncSession, *, user_id: uuid.UUID, rule_id: uuid.UUID) -> AutomationRule:
    """Fetch a single automation rule by ID."""
    result = await session.execute(
        select(AutomationRule).where(AutomationRule.id == rule_id, AutomationRule.user_id == user_id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Automation rule not found")
    return rule


async def create_rule(
    session: AsyncSession, *, user_id: uuid.UUID, payload: AutomationRuleCreate
) -> AutomationRule:
    """Create a new automation rule."""
    rule = AutomationRule(
        user_id=user_id,
        name=payload.name,
        description=payload.description,
        enabled=payload.enabled,
        trigger_type=payload.trigger_type,
        trigger_config=payload.trigger_config,
        action_type=payload.action_type,
        action_config=payload.action_config,
    )
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return rule


async def update_rule(
    session: AsyncSession, *, rule: AutomationRule, payload: AutomationRuleUpdate
) -> AutomationRule:
    """Update an automation rule."""
    fields = payload.model_fields_set
    if "name" in fields and payload.name is not None:
        rule.name = payload.name
    if "description" in fields:
        rule.description = payload.description
    if "enabled" in fields and payload.enabled is not None:
        rule.enabled = payload.enabled
    if "trigger_type" in fields and payload.trigger_type is not None:
        rule.trigger_type = payload.trigger_type
    if "trigger_config" in fields:
        rule.trigger_config = payload.trigger_config
    if "action_type" in fields and payload.action_type is not None:
        rule.action_type = payload.action_type
    if "action_config" in fields:
        rule.action_config = payload.action_config
    await session.commit()
    await session.refresh(rule)
    return rule


async def delete_rule(session: AsyncSession, *, rule: AutomationRule) -> None:
    """Delete an automation rule."""
    await session.delete(rule)
    await session.commit()


async def run_rule(session: AsyncSession, *, rule: AutomationRule, requested_by: uuid.UUID) -> dict[str, Any]:
    """Execute an automation rule and update its last-run metadata."""
    async def _fallback() -> dict[str, Any]:
        return await automation_engine.execute_rule(
            session,
            rule=rule,
            requested_by=requested_by,
            allow_disabled=True,
        )

    result = await task_queue.enqueue_or_run(
        run_automation_rule_job,
        fallback=_fallback,
        queue_name="integrations",
        timeout_seconds=30,
        description=f"automation:{rule.id}",
        rule_id=str(rule.id),
        requested_by=str(requested_by),
        allow_disabled=True,
    )
    return result
