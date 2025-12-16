from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.schema.base import ORMModel


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class TagRead(ORMModel):
    id: UUID
    name: str


class TagAssignmentPayload(BaseModel):
    media_item_id: UUID
