"""Menu and course schemas for request/response payloads."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schema.base import ORMModel
from app.schema.media import MediaItemBase


class CourseItemCreate(BaseModel):
    """Payload for adding an item to a course."""
    media_item_id: UUID
    notes: str | None = None
    position: int


class CourseItemUpdate(BaseModel):
    """Payload for updating a course item annotation."""
    notes: str | None = None
    expected_updated_at: datetime | None = None


class CourseItemReorder(BaseModel):
    """Payload for reordering course items."""
    item_ids: list[UUID]


class CourseItemRead(ORMModel):
    """Course item representation returned by the API."""
    id: UUID
    media_item_id: UUID
    notes: str | None = None
    position: int
    updated_at: datetime
    media_item: MediaItemBase | None = None


class CourseCreate(BaseModel):
    """Payload for creating a menu course."""
    title: str
    description: str | None = None
    intent: str | None = None
    position: int
    items: list[CourseItemCreate] = Field(default_factory=list)


class CourseUpdate(BaseModel):
    """Payload for updating course details."""
    title: str | None = None
    description: str | None = None
    intent: str | None = None
    expected_updated_at: datetime | None = None


class CourseRead(ORMModel):
    """Course representation returned by the API."""
    id: UUID
    title: str
    description: str | None = None
    intent: str | None = None
    position: int
    updated_at: datetime
    items: list[CourseItemRead] = Field(default_factory=list)


class MenuCreate(BaseModel):
    """Payload for creating a menu with optional courses."""
    title: str
    description: str | None = None
    is_public: bool = False
    courses: list[CourseCreate] = Field(default_factory=list)


class MenuUpdate(BaseModel):
    """Payload for updating menu metadata."""
    title: str | None = None
    description: str | None = None
    is_public: bool | None = None


class MenuRead(ORMModel):
    """Menu representation returned to authenticated users."""
    id: UUID
    title: str
    description: str | None = None
    slug: str
    is_public: bool
    owner_id: UUID
    created_at: datetime
    updated_at: datetime
    courses: list[CourseRead] = Field(default_factory=list)


class PublicMenuRead(ORMModel):
    """Menu representation safe for public sharing."""
    id: UUID
    title: str
    description: str | None = None
    slug: str
    is_public: bool
    created_at: datetime
    updated_at: datetime
    courses: list[CourseRead] = Field(default_factory=list)
