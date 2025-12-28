"""Search query/response schemas for internal and external catalogs."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.models.media import MediaType
from app.schema.media import AvailabilitySummary, MediaItemBase


class SearchQuery(BaseModel):
    """Search request payload including optional external fan-out."""
    q: str
    types: list[MediaType] | None = None
    include_external: bool = False


class SearchResultItem(MediaItemBase):
    """Search result with optional external preview metadata."""
    preview_id: UUID | None = None
    source_name: str | None = None
    source_id: str | None = None
    preview_expires_at: datetime | None = None
    in_collection: bool = False
    availability_summary: AvailabilitySummary | None = None


class SearchResult(BaseModel):
    """Search response wrapper for grouped results."""
    results: list[SearchResultItem]
    source: str
    metadata: dict[str, Any] | None = None
