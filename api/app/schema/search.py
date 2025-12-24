from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.models.media import MediaType
from app.schema.media import MediaItemBase


class SearchQuery(BaseModel):
    q: str
    types: list[MediaType] | None = None
    include_external: bool = False


class SearchResultItem(MediaItemBase):
    preview_id: UUID | None = None
    source_name: str | None = None
    source_id: str | None = None
    preview_expires_at: datetime | None = None


class SearchResult(BaseModel):
    results: list[SearchResultItem]
    source: str
    metadata: dict[str, Any] | None = None
