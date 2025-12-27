"""Tagging-related request/response schemas."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.schema.base import ORMModel


class TagCreate(BaseModel):
    """Payload for creating a new tag."""
    name: str = Field(min_length=1, max_length=64)


class TagRead(ORMModel):
    """Tag representation returned by the API."""
    id: UUID
    name: str


class TagAssignmentPayload(BaseModel):
    """Payload for assigning/unassigning tags to media."""
    media_item_id: UUID
