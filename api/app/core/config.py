"""Application settings parsed from environment variables and defaults."""

import json
from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    app_name: str = "Tastebuds API"
    environment: str = "development"
    api_prefix: str = "/api"

    database_url: str
    test_database_url: Optional[str] = None

    access_token_expires_minutes: int = 30
    refresh_token_expires_minutes: int = 60 * 24 * 7
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"

    google_books_api_key: Optional[str] = None
    tmdb_api_key: Optional[str] = None
    tmdb_api_auth_header: Optional[str] = None
    igdb_client_id: Optional[str] = None
    igdb_client_secret: Optional[str] = None
    lastfm_api_key: Optional[str] = None

    log_level: str = "INFO"
    cors_origins: list[str] | str = Field(default_factory=lambda: DEFAULT_CORS_ORIGINS.copy())
    external_search_quota_max_requests: int = 10
    external_search_quota_window_seconds: int = 60
    external_search_preview_ttl_seconds: int = 300
    external_search_preview_max_payload_bytes: int = 50_000
    external_search_preview_max_metadata_bytes: int = 20_000
    ingestion_payload_retention_days: int = 90
    ingestion_payload_max_bytes: int = 250_000
    ingestion_metadata_max_bytes: int = 50_000
    availability_refresh_days: int = 7
    taste_profile_refresh_hours: int = 24
    draft_share_token_ttl_days: int = 7
    credential_vault_key: Optional[str] = None
    ops_admin_emails: list[str] | str = Field(default_factory=list)
    redis_url: str = "redis://redis:6379/0"
    worker_queue_names: list[str] | str = Field(
        default_factory=lambda: ["default", "ingestion", "integrations", "maintenance", "webhooks", "sync"]
    )
    health_allowlist: list[str] | str = Field(default_factory=list)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: str | list[str] | None) -> list[str]:
        """Normalize CORS origins from JSON, CSV, or list inputs."""
        if isinstance(value, list):
            cleaned = [origin.strip() for origin in value if isinstance(origin, str) and origin.strip()]
            return cleaned or DEFAULT_CORS_ORIGINS.copy()
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return DEFAULT_CORS_ORIGINS.copy()
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                cleaned = [str(origin).strip() for origin in parsed if str(origin).strip()]
                if cleaned:
                    return cleaned
            origins = [origin.strip() for origin in stripped.split(",") if origin.strip()]
            if origins:
                return origins
        return DEFAULT_CORS_ORIGINS.copy()

    @model_validator(mode="after")
    def _validate_tmdb_credentials(self) -> "Settings":
        """Ensure TMDB credentials are present before enabling ingestion."""
        if not (self.tmdb_api_auth_header or self.tmdb_api_key):
            msg = "TMDB_API_AUTH_HEADER (preferred) or TMDB_API_KEY must be set for TMDB ingestion"
            raise ValueError(msg)
        return self

    @field_validator("worker_queue_names", mode="before")
    @classmethod
    def _split_worker_queue_names(cls, value: str | list[str] | None) -> list[str]:
        """Normalize worker queue names from JSON, CSV, or list inputs."""
        if isinstance(value, list):
            cleaned = [item.strip() for item in value if isinstance(item, str) and item.strip()]
            if cleaned:
                return cleaned
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return ["default"]
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                cleaned = [str(item).strip() for item in parsed if str(item).strip()]
                if cleaned:
                    return cleaned
            names = [item.strip() for item in stripped.split(",") if item.strip()]
            if names:
                return names
        return ["default"]

    @field_validator("health_allowlist", mode="before")
    @classmethod
    def _split_health_allowlist(cls, value: str | list[str] | None) -> list[str]:
        """Normalize health allowlist entries from JSON, CSV, or list inputs."""
        if isinstance(value, list):
            cleaned = [item.strip() for item in value if isinstance(item, str) and item.strip()]
            return cleaned
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                cleaned = [str(item).strip() for item in parsed if str(item).strip()]
                return cleaned
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return []

    @field_validator("ops_admin_emails", mode="before")
    @classmethod
    def _split_ops_admin_emails(cls, value: str | list[str] | None) -> list[str]:
        """Normalize ops admin emails from JSON, CSV, or list inputs."""
        if isinstance(value, list):
            return [email.strip().lower() for email in value if isinstance(email, str) and email.strip()]
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                return [str(email).strip().lower() for email in parsed if str(email).strip()]
            return [email.strip().lower() for email in stripped.split(",") if email.strip()]
        return []

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Return cached settings to avoid re-parsing environment variables."""
    return Settings()


settings = get_settings()
