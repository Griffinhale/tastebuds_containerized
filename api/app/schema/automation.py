"""Automation rule schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schema.base import ORMModel


class AutomationRuleCreate(BaseModel):
    """Payload for creating an automation rule."""
    name: str
    description: str | None = None
    enabled: bool = True
    trigger_type: str
    trigger_config: dict | None = None
    action_type: str
    action_config: dict | None = None


class AutomationRuleUpdate(BaseModel):
    """Payload for updating an automation rule."""
    name: str | None = None
    description: str | None = None
    enabled: bool | None = None
    trigger_type: str | None = None
    trigger_config: dict | None = None
    action_type: str | None = None
    action_config: dict | None = None


class AutomationRuleRead(ORMModel):
    """Automation rule representation."""
    id: UUID
    name: str
    description: str | None = None
    enabled: bool
    trigger_type: str
    trigger_config: dict | None = None
    action_type: str
    action_config: dict | None = None
    last_run_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime


class AutomationRunResponse(BaseModel):
    """Automation rule execution summary."""
    rule_id: UUID
    status: str
    ran_at: datetime
    detail: dict | None = None
