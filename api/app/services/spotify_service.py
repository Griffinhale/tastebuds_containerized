"""Spotify OAuth, token refresh, and playlist export helpers."""

from __future__ import annotations

import base64
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.ingestion.base import ConnectorResult
from app.ingestion.http import ExternalAPIError
from app.models.credential import UserCredential
from app.models.media import MediaType
from app.models.menu import Menu
from app.services import media_service
from app.services.credential_vault import credential_vault
from app.utils.datetime import parse_date

SPOTIFY_AUTH_BASE = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"
DEFAULT_SPOTIFY_SCOPES = [
    "playlist-modify-private",
    "playlist-modify-public",
    "user-read-email",
]


def _utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    now = datetime.utcnow()
    return now if now.tzinfo else now.replace(tzinfo=timezone.utc)


def _require_spotify_credentials() -> tuple[str, str]:
    """Ensure Spotify client credentials are configured."""
    if not settings.spotify_client_id or not settings.spotify_client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Spotify credentials missing",
        )
    return settings.spotify_client_id, settings.spotify_client_secret


def build_state_token(user_id: uuid.UUID) -> str:
    """Create a short-lived state token for Spotify OAuth."""
    now = _utcnow()
    payload = {
        "sub": str(user_id),
        "type": "spotify_state",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=10)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_state_token(token: str) -> uuid.UUID:
    """Validate a Spotify OAuth state token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state token") from exc
    if payload.get("type") != "spotify_state" or not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state token")
    return uuid.UUID(str(payload["sub"]))


def build_authorize_url(state: str, *, redirect_uri: str | None = None) -> str:
    """Compose the Spotify OAuth authorization URL."""
    client_id, _ = _require_spotify_credentials()
    redirect = redirect_uri or settings.spotify_redirect_uri
    if not redirect:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Spotify redirect URI missing")
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect,
        "scope": " ".join(settings.spotify_scopes or DEFAULT_SPOTIFY_SCOPES),
        "state": state,
    }
    return f"{SPOTIFY_AUTH_BASE}?{urlencode(params)}"


async def exchange_code_for_token(code: str, *, redirect_uri: str | None = None) -> dict[str, Any]:
    """Exchange an OAuth code for Spotify tokens."""
    client_id, client_secret = _require_spotify_credentials()
    redirect = redirect_uri or settings.spotify_redirect_uri
    if not redirect:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Spotify redirect URI missing")
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("utf-8")
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect,
    }
    headers = {"Authorization": f"Basic {auth}"}
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(SPOTIFY_TOKEN_URL, data=data, headers=headers)
    if response.status_code >= 400:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Spotify token exchange failed")
    return response.json()


async def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    """Refresh an access token with the Spotify refresh token."""
    client_id, client_secret = _require_spotify_credentials()
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("utf-8")
    data = {"grant_type": "refresh_token", "refresh_token": refresh_token}
    headers = {"Authorization": f"Basic {auth}"}
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(SPOTIFY_TOKEN_URL, data=data, headers=headers)
    if response.status_code >= 400:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Spotify token refresh failed")
    return response.json()


async def store_tokens(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: dict[str, Any],
) -> UserCredential:
    """Store Spotify tokens in the credential vault."""
    expires_in = int(payload.get("expires_in") or 0)
    expires_at = _utcnow() + timedelta(seconds=expires_in) if expires_in else None
    secret_payload = {
        "access_token": payload.get("access_token"),
        "refresh_token": payload.get("refresh_token"),
        "scope": payload.get("scope"),
        "token_type": payload.get("token_type"),
    }
    return await credential_vault.store_secret(
        session,
        user_id=user_id,
        provider="spotify",
        secret_payload=secret_payload,
        expires_at=expires_at,
    )


async def _get_spotify_credential(
    session: AsyncSession, *, user_id: uuid.UUID
) -> tuple[dict[str, Any] | None, datetime | None]:
    """Return decrypted tokens and expiry for Spotify."""
    payload = await credential_vault.get_secret(session, user_id=user_id, provider="spotify", allow_expired=True)
    expires_at = await session.scalar(
        select(UserCredential.expires_at).where(
            UserCredential.user_id == user_id,
            UserCredential.provider == "spotify",
        )
    )
    return payload, expires_at


async def ensure_access_token(session: AsyncSession, *, user_id: uuid.UUID) -> str:
    """Fetch or refresh a Spotify access token."""
    payload, expires_at = await _get_spotify_credential(session, user_id=user_id)
    if not payload or not payload.get("access_token"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spotify not connected")
    now = _utcnow()
    should_refresh = expires_at and expires_at <= now + timedelta(minutes=5)
    if not should_refresh:
        return str(payload["access_token"])
    refresh_token = payload.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Spotify refresh token missing")
    refreshed = await refresh_access_token(str(refresh_token))
    refreshed["refresh_token"] = refresh_token
    await store_tokens(session, user_id=user_id, payload=refreshed)
    return str(refreshed["access_token"])


async def rotate_tokens(session: AsyncSession, *, user_id: uuid.UUID) -> dict[str, Any]:
    """Rotate Spotify tokens via the refresh flow."""
    payload, _ = await _get_spotify_credential(session, user_id=user_id)
    if not payload or not payload.get("refresh_token"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spotify not connected")
    refreshed = await refresh_access_token(str(payload["refresh_token"]))
    refreshed["refresh_token"] = payload.get("refresh_token")
    await store_tokens(session, user_id=user_id, payload=refreshed)
    return {"status": "rotated", "provider": "spotify", "rotated_at": _utcnow().isoformat() + "Z"}


async def _spotify_request(
    method: str, path: str, *, access_token: str, params: dict[str, Any] | None = None, json: dict | None = None
) -> dict[str, Any]:
    """Issue a Spotify API request and return JSON."""
    url = f"{SPOTIFY_API_BASE}{path}"
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.request(method, url, headers=headers, params=params, json=json)
    if response.status_code >= 400:
        raise ExternalAPIError(f"Spotify API error {response.status_code}")
    return response.json()


async def create_playlist(
    access_token: str, *, name: str, description: str | None, public: bool
) -> dict[str, Any]:
    """Create a playlist for the current Spotify user."""
    payload = {"name": name, "public": public, "description": description or ""}
    return await _spotify_request("POST", "/me/playlists", access_token=access_token, json=payload)


async def add_tracks(access_token: str, *, playlist_id: str, uris: list[str]) -> None:
    """Add tracks to a Spotify playlist in batches."""
    for i in range(0, len(uris), 100):
        batch = uris[i : i + 100]
        await _spotify_request(
            "POST",
            f"/playlists/{playlist_id}/tracks",
            access_token=access_token,
            json={"uris": batch},
        )


async def search_track(
    access_token: str, *, query: str, market: str | None = None
) -> dict[str, Any] | None:
    """Search Spotify for a track and return the first match."""
    params: dict[str, Any] = {"q": query, "type": "track", "limit": 1}
    if market:
        params["market"] = market
    data = await _spotify_request("GET", "/search", access_token=access_token, params=params)
    items = data.get("tracks", {}).get("items", [])
    return items[0] if items else None


def build_search_query(title: str, artist: str | None) -> str:
    """Build a Spotify search query for a track."""
    if artist:
        return f'track:"{title}" artist:"{artist}"'
    return f'track:"{title}"'


def track_to_connector_result(track: dict[str, Any]) -> ConnectorResult:
    """Convert a Spotify track payload into a connector result."""
    artists = track.get("artists") or []
    artist_name = artists[0].get("name") if artists else None
    album = track.get("album") or {}
    release_date = parse_date(album.get("release_date"))
    metadata = {
        "spotify_uri": track.get("uri"),
        "popularity": track.get("popularity"),
        "explicit": track.get("explicit"),
    }
    extensions = {
        "music": {
            "artist_name": artist_name,
            "album_name": album.get("name"),
            "track_number": track.get("track_number"),
            "duration_ms": track.get("duration_ms"),
        }
    }
    return ConnectorResult(
        media_type=MediaType.MUSIC,
        title=track.get("name") or "Unknown",
        description=None,
        release_date=release_date,
        cover_image_url=(album.get("images") or [{}])[0].get("url"),
        canonical_url=track.get("external_urls", {}).get("spotify"),
        metadata=metadata,
        source_name="spotify",
        source_id=track.get("id") or track.get("uri") or "",
        source_url=track.get("external_urls", {}).get("spotify"),
        raw_payload=track,
        extensions=extensions,
    )


async def ingest_track(session: AsyncSession, *, track: dict[str, Any]) -> None:
    """Ingest a Spotify track into the media catalog."""
    result = track_to_connector_result(track)
    await media_service.upsert_media(session, result)


async def export_menu(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    menu: Menu,
    payload: Any,
) -> dict[str, Any]:
    """Export menu music items into a Spotify playlist."""
    access_token = await ensure_access_token(session, user_id=user_id)
    playlist_name = payload.playlist_name or menu.title
    description = payload.description or menu.description or "Tastebuds menu export"
    try:
        playlist = await create_playlist(
            access_token,
            name=playlist_name,
            description=description,
            public=payload.public,
        )
    except ExternalAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    track_uris: list[str] = []
    not_found: list[str] = []
    imported = 0
    for course in menu.courses:
        for item in course.items:
            media_item = item.media_item
            if not media_item or media_item.media_type != MediaType.MUSIC:
                continue
            artist = media_item.music.artist_name if media_item.music else None
            query = build_search_query(media_item.title, artist)
            try:
                match = await search_track(access_token, query=query, market=payload.market)
            except ExternalAPIError as exc:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
            if not match:
                label = f"{media_item.title} — {artist}" if artist else media_item.title
                not_found.append(label)
                continue
            uri = match.get("uri")
            if uri:
                track_uris.append(uri)
            if payload.import_tracks:
                await ingest_track(session, track=match)
                imported += 1
    if track_uris:
        try:
            await add_tracks(access_token, playlist_id=playlist["id"], uris=track_uris)
        except ExternalAPIError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return {
        "playlist_id": playlist["id"],
        "playlist_url": playlist.get("external_urls", {}).get("spotify", ""),
        "tracks_added": len(track_uris),
        "tracks_skipped": len(not_found),
        "tracks_not_found": not_found,
        "imported_tracks": imported,
    }
