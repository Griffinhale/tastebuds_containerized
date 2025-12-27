"""Media-related schemas for catalog responses and updates."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.media import MediaType, UserItemLogType, UserItemStatus
from app.schema.base import ORMModel


class MediaSourceRead(ORMModel):
    """Source metadata returned with media items."""
    id: UUID
    source_name: str
    external_id: str
    canonical_url: str | None = None
    fetched_at: datetime


class MediaItemBase(ORMModel):
    """Shared fields for media item responses."""
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
    """Media item response with attached sources."""
    sources: list[MediaSourceRead] = []


class MediaItemUpsert(BaseModel):
    """Payload for upserting a media item."""
    media_type: MediaType
    title: str
    subtitle: str | None = None
    description: str | None = None
    release_date: date | None = None
    cover_image_url: str | None = None
    canonical_url: str | None = None
    metadata: dict | None = Field(default_factory=dict)


class UserItemStateRead(ORMModel):
    """User-specific media status details."""
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
    """Payload for updating a user's media state."""
    status: UserItemStatus
    rating: int | None = Field(default=None, ge=0, le=10)
    favorite: bool = False
    notes: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class UserItemLogRead(ORMModel):
    """User log entry fields for timeline views."""
    id: UUID
    user_id: UUID
    media_item_id: UUID
    log_type: UserItemLogType
    notes: str | None = None
    minutes_spent: int | None = None
    progress_percent: int | None = None
    goal_target: str | None = None
    goal_due_on: date | None = None
    logged_at: datetime
    created_at: datetime
    updated_at: datetime
    media_item: MediaItemBase | None = None


class UserItemLogCreate(BaseModel):
    """Payload for creating a log entry."""
    media_item_id: UUID
    log_type: UserItemLogType
    notes: str | None = None
    minutes_spent: int | None = Field(default=None, ge=0)
    progress_percent: int | None = Field(default=None, ge=0, le=100)
    goal_target: str | None = None
    goal_due_on: date | None = None
    logged_at: datetime | None = None


class UserItemLogUpdate(BaseModel):
    """Payload for updating a log entry."""
    log_type: UserItemLogType | None = None
    notes: str | None = None
    minutes_spent: int | None = Field(default=None, ge=0)
    progress_percent: int | None = Field(default=None, ge=0, le=100)
    goal_target: str | None = None
    goal_due_on: date | None = None
    logged_at: datetime | None = None
