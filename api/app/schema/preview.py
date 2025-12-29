"""Preview detail schemas for external search results."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.media import MediaType
from app.schema.media import BookDetail, GameDetail, MovieDetail, MusicDetail


class ExternalPreviewDetail(BaseModel):
    """Preview detail payload for an external search result."""
    preview_id: UUID
    media_type: MediaType
    title: str
    subtitle: str | None = None
    description: str | None = None
    release_date: date | None = None
    cover_image_url: str | None = None
    canonical_url: str | None = None
    metadata: dict | None = None
    source_name: str
    source_id: str
    source_url: str | None = None
    preview_expires_at: datetime | None = None
    book: BookDetail | None = None
    movie: MovieDetail | None = None
    game: GameDetail | None = None
    music: MusicDetail | None = None
