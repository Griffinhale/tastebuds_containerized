"""Automation rule endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schema.automation import (
    AutomationRuleCreate,
    AutomationRuleRead,
    AutomationRuleUpdate,
    AutomationRunResponse,
)
from app.services import automation_service

router = APIRouter()


@router.get("", response_model=list[AutomationRuleRead])
async def list_automation_rules(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AutomationRuleRead]:
    """List automation rules for the current user."""
    rules = await automation_service.list_rules(session, user_id=current_user.id)
    return [AutomationRuleRead.model_validate(rule) for rule in rules]


@router.post("", response_model=AutomationRuleRead, status_code=status.HTTP_201_CREATED)
async def create_automation_rule(
    payload: AutomationRuleCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AutomationRuleRead:
    """Create a new automation rule."""
    rule = await automation_service.create_rule(session, user_id=current_user.id, payload=payload)
    return AutomationRuleRead.model_validate(rule)


@router.patch("/{rule_id}", response_model=AutomationRuleRead)
async def update_automation_rule(
    rule_id: uuid.UUID,
    payload: AutomationRuleUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AutomationRuleRead:
    """Update an automation rule."""
    rule = await automation_service.get_rule(session, user_id=current_user.id, rule_id=rule_id)
    rule = await automation_service.update_rule(session, rule=rule, payload=payload)
    return AutomationRuleRead.model_validate(rule)


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def delete_automation_rule(
    rule_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete an automation rule."""
    rule = await automation_service.get_rule(session, user_id=current_user.id, rule_id=rule_id)
    await automation_service.delete_rule(session, rule=rule)


@router.post("/{rule_id}/run", response_model=AutomationRunResponse)
async def run_automation_rule(
    rule_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AutomationRunResponse:
    """Trigger an automation rule immediately."""
    rule = await automation_service.get_rule(session, user_id=current_user.id, rule_id=rule_id)
    result = await automation_service.run_rule(session, rule=rule, requested_by=current_user.id)
    return AutomationRunResponse(
        rule_id=rule.id,
        status=result["status"],
        ran_at=result["ran_at"],
        detail=result.get("detail"),
    )
