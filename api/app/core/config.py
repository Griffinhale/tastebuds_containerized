from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
