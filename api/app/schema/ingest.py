from __future__ import annotations

from pydantic import BaseModel, Field

from app.schema.media import MediaItemDetail


class IngestRequest(BaseModel):
    external_id: str | None = None
    url: str | None = None
    force_refresh: bool = Field(default=False)


class IngestResponse(BaseModel):
    media_item: MediaItemDetail
    source_name: str
