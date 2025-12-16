from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.models.media import MediaType
from app.schema.media import MediaItemBase


class SearchQuery(BaseModel):
    q: str
    types: list[MediaType] | None = None
    include_external: bool = False


class SearchResult(BaseModel):
    results: list[MediaItemBase]
    source: str
    metadata: dict[str, Any] | None = None
