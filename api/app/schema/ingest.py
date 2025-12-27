"""Ingestion request/response schemas for preview ingestion."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schema.media import MediaItemDetail


class IngestRequest(BaseModel):
    """Payload to ingest an external preview into the catalog."""
    external_id: str | None = None
    url: str | None = None
    force_refresh: bool = Field(default=False)


class IngestResponse(BaseModel):
    """Response for ingestion requests with the stored media item."""
    media_item: MediaItemDetail
    source_name: str
