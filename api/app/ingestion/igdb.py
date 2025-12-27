"""IGDB connector for game metadata ingestion."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.core.config import settings
from app.ingestion.base import BaseConnector, ConnectorResult
from app.ingestion.http import ExternalAPIError
from app.models.media import MediaType


class IGDBConnector(BaseConnector):
    """IGDB API connector with token caching."""
    source_name = "igdb"
    _token_url = "https://id.twitch.tv/oauth2/token"
    _game_url = "https://api.igdb.com/v4/games"
    _token_refresh_buffer_seconds = 30

    def __init__(self, client_id: str | None = None, client_secret: str | None = None) -> None:
        self.client_id = client_id or settings.igdb_client_id
        self.client_secret = client_secret or settings.igdb_client_secret
        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None

    def _utcnow(self) -> datetime:
        """Return a timezone-aware UTC timestamp."""
        now = datetime.utcnow()
        return now if now.tzinfo else now.replace(tzinfo=timezone.utc)

    def _reset_token_cache(self) -> None:
        """Clear cached access token state."""
        self._access_token = None
        self._token_expires_at = None

    def _needs_token_refresh(self) -> bool:
        """Return True when the cached token is missing or expiring."""
        if not self._access_token or not self._token_expires_at:
            return True
        refresh_buffer = timedelta(seconds=max(self._token_refresh_buffer_seconds, 0))
        expiry = self._token_expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return self._utcnow() + refresh_buffer >= expiry

    async def _ensure_token(self, force_refresh: bool = False) -> str:
        """Ensure a valid bearer token is available for requests."""
        if not self.client_id or not self.client_secret:
            raise ExternalAPIError("IGDB credentials missing")
        if not force_refresh and not self._needs_token_refresh():
            return self._access_token  # type: ignore[return-value]

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                self._token_url,
                params={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "client_credentials",
                },
            )
        response.raise_for_status()
        data = response.json()
        token = data.get("access_token")
        if not token:
            raise ExternalAPIError("Failed to fetch IGDB token")
        expires_value = data.get("expires_in")
        expires_seconds = 0
        if expires_value is not None:
            try:
                expires_seconds = int(expires_value)
            except (TypeError, ValueError):
                expires_seconds = 0
        if expires_seconds <= 0:
            expires_seconds = 60
        self._access_token = token
        self._token_expires_at = self._utcnow() + timedelta(seconds=expires_seconds)
        return token

    async def _authenticated_post(self, content: str) -> list[dict[str, Any]]:
        """POST an IGDB query with automatic token refresh on 401s."""
        for attempt in range(2):
            token = await self._ensure_token(force_refresh=(attempt > 0))
            headers = {
                "Client-ID": self.client_id or "",
                "Authorization": f"Bearer {token}",
            }
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(self._game_url, content=content, headers=headers)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:  # pragma: no cover - rare race conditions handled upstream
                if exc.response.status_code == 401:
                    self._reset_token_cache()
                    if attempt == 0:
                        continue
                raise
            payload = response.json()
            if isinstance(payload, list):
                return payload
            return []
        raise ExternalAPIError("IGDB request failed after refreshing token")

    async def fetch(self, identifier: str) -> ConnectorResult:
        """Fetch a game record by IGDB ID."""
        query = (
            "fields name,summary,first_release_date,cover.url,genres.name,platforms.name,"
            "involved_companies.company.name,involved_companies.publisher,involved_companies.developer;"
            f" where id = {identifier};"
        )
        body = await self._authenticated_post(query)
        if not body:
            raise ExternalAPIError("IGDB resource not found")
        payload = body[0]
        cover = payload.get("cover", {})
        image_url = cover.get("url")
        release_stamp = payload.get("first_release_date")
        release_date = None
        if release_stamp:
            release_date = datetime.utcfromtimestamp(release_stamp).date()
        metadata = {
            "genres": [g.get("name") for g in payload.get("genres", []) if g.get("name")],
            "platforms": [p.get("name") for p in payload.get("platforms", []) if p.get("name")],
        }
        companies = payload.get("involved_companies", [])
        developers = [c.get("company", {}).get("name") for c in companies if c.get("developer")]
        publishers = [c.get("company", {}).get("name") for c in companies if c.get("publisher")]
        extensions = {
            "game": {
                "platforms": metadata["platforms"],
                "developers": developers,
                "publishers": publishers,
                "genres": metadata["genres"],
            }
        }
        return ConnectorResult(
            media_type=MediaType.GAME,
            title=payload.get("name") or "Unknown",
            description=payload.get("summary"),
            release_date=release_date,
            cover_image_url=image_url,
            canonical_url=None,
            metadata=metadata,
            source_name=self.source_name,
            source_id=str(payload.get("id")),
            source_url=f"https://www.igdb.com/games/{payload.get('slug', payload.get('id'))}",
            raw_payload=payload,
            extensions=extensions,
        )

    async def search(self, query: str, limit: int = 3) -> list[str]:
        """Search IGDB for matching game IDs."""
        igdb_query = f'search "{query}"; fields id; limit {limit};'
        data = await self._authenticated_post(igdb_query)
        return [str(item["id"]) for item in data if item.get("id")]
