from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.media import MediaType, UserItemStatus
from app.schema.base import ORMModel


class MediaSourceRead(ORMModel):
    id: UUID
    source_name: str
    external_id: str
    canonical_url: str | None = None
    fetched_at: datetime


class MediaItemBase(ORMModel):
    id: UUID
    media_type: MediaType
    title: str
    subtitle: str | None = None
    description: str | None = None
    release_date: date | None = None
    cover_image_url: str | None = None
    canonical_url: str | None = None
    metadata: dict | None = None


class MediaItemDetail(MediaItemBase):
    sources: list[MediaSourceRead] = []


class MediaItemUpsert(BaseModel):
    media_type: MediaType
    title: str
    subtitle: str | None = None
    description: str | None = None
    release_date: date | None = None
    cover_image_url: str | None = None
    canonical_url: str | None = None
    metadata: dict | None = Field(default_factory=dict)


class UserItemStateRead(ORMModel):
    id: UUID
    media_item_id: UUID
    user_id: UUID
    status: UserItemStatus
    rating: int | None = None
    favorite: bool
    notes: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class UserItemStateUpdate(BaseModel):
    status: UserItemStatus
    rating: int | None = Field(default=None, ge=0, le=10)
    favorite: bool = False
    notes: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
