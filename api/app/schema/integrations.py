"""Integration and automation schemas for API payloads."""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schema.base import ORMModel


class IntegrationProvider(str, enum.Enum):
    """Known integration providers."""
    SPOTIFY = "spotify"
    ARR = "arr"
    JELLYFIN = "jellyfin"
    PLEX = "plex"


class IntegrationAuthType(str, enum.Enum):
    """Authentication mechanism for integrations."""
    OAUTH = "oauth"
    API_KEY = "api_key"


class IntegrationCapabilities(BaseModel):
    """Supported capabilities for a provider."""
    supports_webhooks: bool = False
    supports_export: bool = False
    supports_sync: bool = False


class IntegrationStatusRead(BaseModel):
    """Summary status for a provider connection."""
    provider: IntegrationProvider
    display_name: str
    auth_type: IntegrationAuthType
    connected: bool
    status: str
    expires_at: datetime | None = None
    rotated_at: datetime | None = None
    last_error: str | None = None
    webhook_token_prefix: str | None = None
    capabilities: IntegrationCapabilities = Field(default_factory=IntegrationCapabilities)


class IntegrationCredentialUpdate(BaseModel):
    """Payload for storing headless integration credentials."""
    payload: dict[str, str] = Field(default_factory=dict)
    expires_at: datetime | None = None


class IntegrationWebhookTokenRead(BaseModel):
    """Webhook token details for configuration."""
    provider: IntegrationProvider
    webhook_url: str
    token_prefix: str


class IntegrationIngestEventRead(ORMModel):
    """Ingest queue event read model."""
    id: UUID
    provider: str
    event_type: str | None = None
    source_name: str | None = None
    source_id: str | None = None
    title: str | None = None
    status: str
    error: str | None = None
    media_item_id: UUID | None = None
    created_at: datetime
    processed_at: datetime | None = None


class SpotifyExportRequest(BaseModel):
    """Payload for exporting a menu to Spotify."""
    playlist_name: str | None = None
    description: str | None = None
    public: bool = False
    import_tracks: bool = False
    market: str | None = None


class SpotifyExportResponse(BaseModel):
    """Spotify export summary payload."""
    playlist_id: str
    playlist_url: str
    tracks_added: int
    tracks_skipped: int
    tracks_not_found: list[str] = Field(default_factory=list)
    imported_tracks: int = 0


class IntegrationSyncRequest(BaseModel):
    """Payload for triggering an integration sync."""
    external_id: str = "library"
    action: str = "sync"
    force_refresh: bool = False
