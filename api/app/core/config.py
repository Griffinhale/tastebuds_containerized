import json
from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator

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
    igdb_client_id: Optional[str] = None
    igdb_client_secret: Optional[str] = None
    lastfm_api_key: Optional[str] = None

    log_level: str = "INFO"
    cors_origins: list[str] | str = Field(default_factory=lambda: DEFAULT_CORS_ORIGINS.copy())

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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
