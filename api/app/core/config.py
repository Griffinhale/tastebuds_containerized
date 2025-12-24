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
    redis_url: str = "redis://redis:6379/0"
    worker_queue_names: list[str] = Field(default_factory=lambda: ["default"])

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: str | list[str] | None) -> list[str]:
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
        if not (self.tmdb_api_auth_header or self.tmdb_api_key):
            msg = "TMDB_API_AUTH_HEADER (preferred) or TMDB_API_KEY must be set for TMDB ingestion"
            raise ValueError(msg)
        return self

    @field_validator("worker_queue_names", mode="before")
    @classmethod
    def _split_worker_queue_names(cls, value: str | list[str] | None) -> list[str]:
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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
