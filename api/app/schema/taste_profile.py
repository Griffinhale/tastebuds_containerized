"""Taste profile schemas for preference summaries."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schema.base import ORMModel


class TasteProfileRead(ORMModel):
    """Materialized taste profile for a user."""
    id: UUID
    user_id: UUID
    generated_at: datetime
    profile: dict = Field(default_factory=dict)


class TasteProfileRefresh(BaseModel):
    """Payload for on-demand taste profile refresh."""
    force: bool = True
