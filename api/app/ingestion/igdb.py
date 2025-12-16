from __future__ import annotations

from datetime import datetime

import httpx

from app.core.config import settings
from app.ingestion.base import BaseConnector, ConnectorResult
from app.ingestion.http import ExternalAPIError
from app.models.media import MediaType


class IGDBConnector(BaseConnector):
    source_name = "igdb"

    def __init__(self, client_id: str | None = None, client_secret: str | None = None) -> None:
        self.client_id = client_id or settings.igdb_client_id
        self.client_secret = client_secret or settings.igdb_client_secret
        self._access_token: str | None = None

    async def _ensure_token(self) -> str:
        if self._access_token:
            return self._access_token
        if not self.client_id or not self.client_secret:
            raise ExternalAPIError("IGDB credentials missing")
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                "https://id.twitch.tv/oauth2/token",
                params={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "client_credentials",
                },
            )
            response.raise_for_status()
            data = response.json()
            self._access_token = data.get("access_token")
            if not self._access_token:
                raise ExternalAPIError("Failed to fetch IGDB token")
            return self._access_token

    async def fetch(self, identifier: str) -> ConnectorResult:
        token = await self._ensure_token()
        query = f"fields name,summary,first_release_date,cover.url,genres.name,platforms.name,involved_companies.company.name,involved_companies.publisher,involved_companies.developer; where id = {identifier};"
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                "https://api.igdb.com/v4/games",
                content=query,
                headers={
                    "Client-ID": self.client_id or "",
                    "Authorization": f"Bearer {token}",
                },
            )
            response.raise_for_status()
            body = response.json()
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
        token = await self._ensure_token()
        igdb_query = f'search "{query}"; fields id; limit {limit};'
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                "https://api.igdb.com/v4/games",
                content=igdb_query,
                headers={
                    "Client-ID": self.client_id or "",
                    "Authorization": f"Bearer {token}",
                },
            )
            response.raise_for_status()
            data = response.json()
        return [str(item["id"]) for item in data if item.get("id")]
