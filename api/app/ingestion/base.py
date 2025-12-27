"""Base connector primitives for external ingestion."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.models.media import MediaType


@dataclass(slots=True)
class ConnectorResult:
    """Normalized connector payload returned by ingestion sources."""
    media_type: MediaType
    title: str
    description: str | None
    release_date: date | None
    cover_image_url: str | None
    canonical_url: str | None
    metadata: dict[str, Any] = field(default_factory=dict)
    source_name: str = ""
    source_id: str = ""
    source_url: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)


class BaseConnector:
    """Abstract connector interface for external sources."""
    source_name: str

    def parse_identifier(self, identifier: str) -> str:
        """Normalize external identifiers before lookup."""
        return identifier.strip()

    async def fetch(self, identifier: str) -> ConnectorResult:
        """Fetch a normalized result by external identifier."""
        raise NotImplementedError

    async def search(self, query: str, limit: int = 3) -> list[str]:
        """Return source-specific identifiers for a search query."""
        return []
