from __future__ import annotations

from urllib.parse import unquote, urlparse

from app.core.config import settings
from app.ingestion.base import BaseConnector, ConnectorResult
from app.ingestion.http import ExternalAPIError, fetch_json
from app.models.media import MediaType
from app.utils.datetime import parse_date


class LastFMConnector(BaseConnector):
    source_name = "lastfm"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.lastfm_api_key

    def parse_identifier(self, identifier: str) -> tuple[str | None, str | None, str | None]:
        artist = track = mbid = None
        if "::" in identifier:
            artist, track = identifier.split("::", 1)
        elif identifier.startswith("http"):
            parsed = urlparse(identifier)
            parts = [unquote(p) for p in parsed.path.split("/") if p]
            if len(parts) >= 3 and parts[0].lower() == "music":
                artist = parts[1]
                track = parts[-1]
        else:
            mbid = identifier
        return artist, track, mbid

    async def fetch(self, identifier: str) -> ConnectorResult:
        artist, track, mbid = self.parse_identifier(identifier)
        if not self.api_key:
            raise ExternalAPIError("Last.fm API key missing")
        params = {
            "api_key": self.api_key,
            "format": "json",
            "method": "track.getInfo",
        }
        if mbid:
            params["mbid"] = mbid
        elif artist and track:
            params["artist"] = artist
            params["track"] = track
        else:
            raise ExternalAPIError("Track identifier required")
        payload = await fetch_json("https://ws.audioscrobbler.com/2.0/", params=params)
        track_info = payload.get("track")
        if not track_info:
            raise ExternalAPIError("Track not found")
        album = track_info.get("album", {})
        tags = [tag.get("name") for tag in track_info.get("toptags", {}).get("tag", []) if tag.get("name")]
        metadata = {
            "listeners": track_info.get("listeners"),
            "playcount": track_info.get("playcount"),
            "tags": tags,
        }
        duration_ms = None
        if track_info.get("duration"):
            try:
                duration_ms = int(track_info["duration"])
            except ValueError:
                duration_ms = None
        extensions = {
            "music": {
                "artist_name": track_info.get("artist", {}).get("name"),
                "album_name": album.get("title"),
                "track_number": album.get("@attr", {}).get("position"),
                "duration_ms": duration_ms,
            }
        }
        return ConnectorResult(
            media_type=MediaType.MUSIC,
            title=track_info.get("name") or "Unknown",
            description=track_info.get("wiki", {}).get("summary"),
            release_date=parse_date(album.get("release_date")),
            cover_image_url=(album.get("image", [{}])[-1].get("#text") or None),
            canonical_url=track_info.get("url"),
            metadata=metadata,
            source_name=self.source_name,
            source_id=track_info.get("mbid") or track_info.get("name"),
            source_url=track_info.get("url"),
            raw_payload=track_info,
            extensions=extensions,
        )

    async def search(self, query: str, limit: int = 3) -> list[str]:
        if not self.api_key:
            return []
        params = {
            "method": "track.search",
            "track": query,
            "limit": limit,
            "api_key": self.api_key,
            "format": "json",
        }
        payload = await fetch_json("https://ws.audioscrobbler.com/2.0/", params=params)
        matches = payload.get("results", {}).get("trackmatches", {}).get("track", []) or []
        identifiers: list[str] = []
        for track in matches:
            name = track.get("name")
            artist = track.get("artist")
            if name and artist:
                identifiers.append(f"{artist}::{name}")
            if len(identifiers) >= limit:
                break
        return identifiers
