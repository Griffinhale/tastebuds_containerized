from __future__ import annotations

from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.ingestion.base import BaseConnector, ConnectorResult
from app.ingestion.http import ExternalAPIError, fetch_json
from app.models.media import MediaType
from app.utils.datetime import parse_date

IMAGE_BASE = "https://image.tmdb.org/t/p/original"


class TMDBConnector(BaseConnector):
    source_name = "tmdb"

    def __init__(self, api_key: str | None = None, auth_token: str | None = None) -> None:
        self.api_key = api_key or settings.tmdb_api_key
        self.auth_token = auth_token or settings.tmdb_api_auth_header

    def parse_identifier(self, identifier: str) -> str:
        if identifier.startswith("http"):
            parsed = urlparse(identifier)
            parts = parsed.path.strip("/").split("/")
            if len(parts) >= 2 and parts[0] in {"movie", "tv"}:
                return f"{parts[0]}:{parts[1]}"
        return super().parse_identifier(identifier)

    def _auth(self) -> tuple[dict[str, str], dict[str, str]]:
        headers: dict[str, str] = {"accept": "application/json"}
        params: dict[str, str] = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        elif self.api_key:
            params["api_key"] = self.api_key
        else:
            raise ExternalAPIError("TMDB API credentials missing; set TMDB_API_AUTH_HEADER or TMDB_API_KEY")
        return headers, params

    async def fetch(self, identifier: str) -> ConnectorResult:
        token = self.parse_identifier(identifier)
        media_type_hint = None
        if ":" in token:
            media_type_hint, token = token.split(":", 1)
        for endpoint in ([media_type_hint] if media_type_hint else ["movie", "tv"]):
            try:
                data = await self._fetch(endpoint, token)
                if data:
                    return data
            except httpx.HTTPStatusError as exc:  # type: ignore[union-attr]
                if exc.response.status_code == 404:
                    continue
                raise
        raise ExternalAPIError("TMDB resource not found")

    async def _fetch(self, kind: str, tmdb_id: str) -> ConnectorResult | None:
        headers, params = self._auth()
        payload = await fetch_json(
            f"https://api.themoviedb.org/3/{kind}/{tmdb_id}",
            headers=headers,
            params={**params, "append_to_response": "credits"},
        )
        if not payload:
            return None
        if kind == "tv":
            title = payload.get("name")
            media_type = MediaType.TV
            runtime = payload.get("episode_run_time", [None])[0]
            directors = [member["name"] for member in payload.get("created_by", [])]
        else:
            title = payload.get("title")
            media_type = MediaType.MOVIE
            runtime = payload.get("runtime")
            directors = [c["name"] for c in payload.get("credits", {}).get("crew", []) if c.get("job") == "Director"]
        metadata = {
            "genres": [g.get("name") for g in payload.get("genres", [])],
            "languages": payload.get("spoken_languages"),
            "status": payload.get("status"),
        }
        extensions = {
            "movie": {
                "runtime_minutes": runtime,
                "directors": directors,
                "producers": [
                    c.get("name")
                    for c in payload.get("credits", {}).get("crew", [])
                    if c.get("job") == "Producer"
                ],
                "tmdb_type": kind,
            }
        }
        poster = payload.get("poster_path")
        return ConnectorResult(
            media_type=media_type,
            title=title or "Unknown",
            description=payload.get("overview"),
            release_date=parse_date(payload.get("release_date") or payload.get("first_air_date")),
            cover_image_url=f"{IMAGE_BASE}{poster}" if poster else None,
            canonical_url=f"https://www.themoviedb.org/{kind}/{tmdb_id}",
            metadata=metadata,
            source_name=self.source_name,
            source_id=tmdb_id,
            source_url=f"https://api.themoviedb.org/3/{kind}/{tmdb_id}",
            raw_payload=payload,
            extensions=extensions,
        )

    async def search(self, query: str, limit: int = 3) -> list[str]:
        try:
            headers, params = self._auth()
        except ExternalAPIError:
            return []
        identifiers: list[str] = []
        seen: set[str] = set()
        for search_kind in ("movie", "tv"):
            payload = await fetch_json(
                f"https://api.themoviedb.org/3/search/{search_kind}",
                headers=headers,
                params={
                    **params,
                    "query": query,
                    "page": 1,
                    "include_adult": "false",
                    "language": "en-US",
                },
            )
            for result in payload.get("results", []):
                tmdb_id = result.get("id")
                title = (result.get("title") or result.get("name") or "").strip()
                if tmdb_id is None or not title:
                    continue
                token = f"{search_kind}:{tmdb_id}"
                if token in seen:
                    continue
                seen.add(token)
                identifiers.append(token)
                if len(identifiers) >= limit:
                    break
            if len(identifiers) >= limit:
                break
        return identifiers
