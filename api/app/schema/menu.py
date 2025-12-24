from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schema.base import ORMModel
from app.schema.media import MediaItemBase


class CourseItemCreate(BaseModel):
    media_item_id: UUID
    notes: str | None = None
    position: int


class CourseItemReorder(BaseModel):
    item_ids: list[UUID]


class CourseItemRead(ORMModel):
    id: UUID
    media_item_id: UUID
    notes: str | None = None
    position: int
    media_item: MediaItemBase | None = None


class CourseCreate(BaseModel):
    title: str
    description: str | None = None
    position: int
    items: list[CourseItemCreate] = Field(default_factory=list)


class CourseRead(ORMModel):
    id: UUID
    title: str
    description: str | None = None
    position: int
    items: list[CourseItemRead] = Field(default_factory=list)


class MenuCreate(BaseModel):
    title: str
    description: str | None = None
    is_public: bool = False
    courses: list[CourseCreate] = Field(default_factory=list)


class MenuUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    is_public: bool | None = None


class MenuRead(ORMModel):
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
    id: UUID
    title: str
    description: str | None = None
    slug: str
    is_public: bool
    created_at: datetime
    updated_at: datetime
    courses: list[CourseRead] = Field(default_factory=list)
