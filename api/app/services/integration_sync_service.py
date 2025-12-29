"""Sync handlers for integration providers.

Invariants:
- Credentials are sourced from the credential vault; auth failures clear stored secrets.
- Jellyfin/Plex syncs only ingest movie/series items that expose TMDB IDs.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from time import monotonic
from typing import TYPE_CHECKING, Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.credential import UserCredential
from app.services import media_service
from app.services.credential_vault import credential_vault

if TYPE_CHECKING:
    from app.services.sync_service import SyncTask

logger = logging.getLogger("app.services.integration_sync")

SUPPORTED_SYNC_PROVIDERS = {"jellyfin", "plex"}
TMDB_GUID_REGEX = re.compile(r"(?:tmdb|themoviedb)://(?P<id>\d+)", re.IGNORECASE)


@dataclass(slots=True)
class SyncItem:
    """Normalized sync target extracted from an integration provider."""
    tmdb_id: str
    media_kind: str
    title: str | None = None


@dataclass(slots=True)
class ScanResult:
    """Provider scan summary for sync operations."""
    items: list[SyncItem] = field(default_factory=list)
    scanned: int = 0
    skipped_missing_tmdb: int = 0
    skipped_unsupported: int = 0
    errors: list[str] = field(default_factory=list)


class IntegrationSyncError(RuntimeError):
    """Raised for sync failures that should be surfaced to the caller."""

    def __init__(self, message: str, *, clear_credentials: bool = False) -> None:
        super().__init__(message)
        self.message = message
        self.clear_credentials = clear_credentials


async def process_integration_sync(session: AsyncSession, task: "SyncTask") -> dict[str, Any]:
    """Handle integration sync tasks for non-ingestion providers."""
    if not task.requested_by:
        return {
            "status": "failed",
            "provider": task.provider,
            "external_id": task.external_id,
            "action": task.action,
            "error": "missing_requester",
            "force_refresh": task.force_refresh,
            "requested_by": None,
            "requested_at": task.requested_at.isoformat() + "Z",
        }
    try:
        if task.provider == "jellyfin":
            return await _sync_jellyfin(session, task)
        if task.provider == "plex":
            return await _sync_plex(session, task)
    except IntegrationSyncError as exc:
        if exc.clear_credentials:
            await credential_vault.clear_on_failure(
                session,
                user_id=task.requested_by,
                provider=task.provider,
                error=exc.message,
            )
        await _note_sync_error(session, user_id=task.requested_by, provider=task.provider, error=exc.message)
        return {
            "status": "failed",
            "provider": task.provider,
            "external_id": task.external_id,
            "action": task.action,
            "error": exc.message,
            "force_refresh": task.force_refresh,
            "requested_by": str(task.requested_by),
            "requested_at": task.requested_at.isoformat() + "Z",
        }
    logger.info("Sync task skipped for %s (provider=%s action=%s)", task.external_id, task.provider, task.action)
    return {
        "status": "skipped",
        "provider": task.provider,
        "external_id": task.external_id,
        "action": task.action,
        "force_refresh": task.force_refresh,
        "requested_by": str(task.requested_by),
        "requested_at": task.requested_at.isoformat() + "Z",
    }


async def _sync_jellyfin(session: AsyncSession, task: "SyncTask") -> dict[str, Any]:
    """Sync Jellyfin library items via stored API credentials."""
    if task.action != "sync":
        raise IntegrationSyncError(f"unsupported_action:{task.action}")
    credentials = await _load_credentials(session, user_id=task.requested_by, provider="jellyfin")
    base_url, api_key = _normalize_credentials(credentials, provider="jellyfin")
    scan = await _scan_jellyfin_library(
        base_url=base_url,
        api_key=api_key,
        library_id=None if task.external_id == "library" else task.external_id,
    )
    summary = await _ingest_scan(session, task, scan, provider="jellyfin")
    await _clear_sync_error(session, user_id=task.requested_by, provider="jellyfin")
    return summary


async def _sync_plex(session: AsyncSession, task: "SyncTask") -> dict[str, Any]:
    """Sync Plex library items via stored API credentials."""
    if task.action != "sync":
        raise IntegrationSyncError(f"unsupported_action:{task.action}")
    credentials = await _load_credentials(session, user_id=task.requested_by, provider="plex")
    base_url, api_key = _normalize_credentials(credentials, provider="plex")
    scan = await _scan_plex_library(
        base_url=base_url,
        token=api_key,
        section_hint=None if task.external_id == "library" else task.external_id,
    )
    summary = await _ingest_scan(session, task, scan, provider="plex")
    await _clear_sync_error(session, user_id=task.requested_by, provider="plex")
    return summary


async def _load_credentials(
    session: AsyncSession, *, user_id: uuid.UUID, provider: str
) -> dict[str, Any]:
    """Fetch stored credentials or raise for missing configuration."""
    payload = await credential_vault.get_secret(session, user_id=user_id, provider=provider)
    if not payload:
        raise IntegrationSyncError("credentials_missing")
    return payload


def _normalize_credentials(payload: dict[str, Any], *, provider: str) -> tuple[str, str]:
    """Normalize base URL and API key/token values."""
    base_url = str(payload.get("base_url") or "").strip().rstrip("/")
    api_key = str(payload.get("api_key") or payload.get("token") or payload.get("access_token") or "").strip()
    if not base_url:
        raise IntegrationSyncError(f"{provider}_base_url_missing")
    if not api_key:
        raise IntegrationSyncError(f"{provider}_api_key_missing")
    return base_url, api_key


async def _scan_jellyfin_library(
    *, base_url: str, api_key: str, library_id: str | None
) -> ScanResult:
    """Pull Jellyfin library items and extract TMDB IDs."""
    result = ScanResult()
    timeout = httpx.Timeout(15.0)
    headers = {"accept": "application/json"}
    async with httpx.AsyncClient(timeout=timeout) as client:
        users = await _jellyfin_request(client, base_url, api_key, "/Users", headers=headers)
        if not isinstance(users, list) or not users:
            raise IntegrationSyncError("jellyfin_user_lookup_failed", clear_credentials=False)
        user_id = users[0].get("Id") if isinstance(users[0], dict) else None
        if not user_id:
            raise IntegrationSyncError("jellyfin_user_missing", clear_credentials=False)
        start_index = 0
        page_size = 200
        while True:
            params = {
                "Recursive": "true",
                "IncludeItemTypes": "Movie,Series",
                "Fields": "ProviderIds",
                "StartIndex": str(start_index),
                "Limit": str(page_size),
            }
            if library_id:
                params["ParentId"] = library_id
            payload = await _jellyfin_request(
                client,
                base_url,
                api_key,
                f"/Users/{user_id}/Items",
                headers=headers,
                params=params,
            )
            items = payload.get("Items", []) if isinstance(payload, dict) else []
            total = payload.get("TotalRecordCount") if isinstance(payload, dict) else None
            for item in items:
                result.scanned += 1
                if not isinstance(item, dict):
                    continue
                media_kind = _jellyfin_media_kind(item.get("Type"))
                if not media_kind:
                    result.skipped_unsupported += 1
                    continue
                tmdb_id = _extract_tmdb_id(item.get("ProviderIds"))
                if not tmdb_id:
                    result.skipped_missing_tmdb += 1
                    continue
                result.items.append(
                    SyncItem(
                        tmdb_id=tmdb_id,
                        media_kind=media_kind,
                        title=item.get("Name"),
                    )
                )
            start_index += page_size
            if total is None or start_index >= int(total):
                break
    return result


async def _scan_plex_library(
    *, base_url: str, token: str, section_hint: str | None
) -> ScanResult:
    """Pull Plex library items and extract TMDB IDs."""
    result = ScanResult()
    timeout = httpx.Timeout(15.0)
    headers = {"accept": "application/json", "X-Plex-Token": token}
    async with httpx.AsyncClient(timeout=timeout) as client:
        container = await _plex_request(client, base_url, "/library/sections", headers=headers)
        sections = container.get("MediaContainer", {}).get("Directory", []) if isinstance(container, dict) else []
        target_sections = _filter_plex_sections(sections, section_hint)
        if section_hint and not target_sections:
            raise IntegrationSyncError("plex_section_not_found")
        for section in target_sections:
            key = section.get("key")
            section_type = section.get("type")
            if not key or section_type not in {"movie", "show"}:
                continue
            media_kind = "movie" if section_type == "movie" else "tv"
            start_index = 0
            page_size = 200
            while True:
                items = await _plex_request(
                    client,
                    base_url,
                    f"/library/sections/{key}/all",
                    headers=headers,
                    params={
                        "type": "1" if section_type == "movie" else "2",
                        "X-Plex-Container-Start": str(start_index),
                        "X-Plex-Container-Size": str(page_size),
                    },
                )
                container = items.get("MediaContainer", {}) if isinstance(items, dict) else {}
                metadata = container.get("Metadata", []) if isinstance(container, dict) else []
                for entry in metadata:
                    result.scanned += 1
                    if not isinstance(entry, dict):
                        continue
                    tmdb_id = _extract_plex_tmdb_id(entry)
                    if not tmdb_id:
                        result.skipped_missing_tmdb += 1
                        continue
                    result.items.append(
                        SyncItem(
                            tmdb_id=tmdb_id,
                            media_kind=media_kind,
                            title=entry.get("title"),
                        )
                    )
                start_index += page_size
                total_size = container.get("totalSize") if isinstance(container, dict) else None
                if not metadata or (total_size is not None and start_index >= int(total_size)):
                    break
    return result


async def _ingest_scan(
    session: AsyncSession,
    task: "SyncTask",
    scan: ScanResult,
    *,
    provider: str,
    time_budget_seconds: int = 90,
) -> dict[str, Any]:
    """Ingest TMDB-backed sync targets into the catalog."""
    started = monotonic()
    ingested = 0
    failed = 0
    errors: list[str] = []
    truncated = False
    for item in scan.items:
        if monotonic() - started > time_budget_seconds:
            truncated = True
            break
        identifier = f"{item.media_kind}:{item.tmdb_id}"
        try:
            await media_service.ingest_from_source(
                session,
                source="tmdb",
                identifier=identifier,
                force_refresh=task.force_refresh,
            )
            ingested += 1
        except Exception as exc:
            failed += 1
            if len(errors) < 5:
                errors.append(str(exc))
    status = "synced"
    if failed and ingested:
        status = "partial"
    elif failed and not ingested:
        status = "failed"
    if truncated:
        status = "partial"
    return {
        "status": status,
        "provider": provider,
        "external_id": task.external_id,
        "action": task.action,
        "scanned": scan.scanned,
        "eligible": len(scan.items),
        "ingested": ingested,
        "failed": failed,
        "skipped_missing_tmdb": scan.skipped_missing_tmdb,
        "skipped_unsupported": scan.skipped_unsupported,
        "errors": errors,
        "truncated": truncated,
        "force_refresh": task.force_refresh,
        "requested_by": str(task.requested_by) if task.requested_by else None,
        "requested_at": task.requested_at.isoformat() + "Z",
    }


def _jellyfin_media_kind(kind: str | None) -> str | None:
    """Translate Jellyfin item types to TMDB kinds."""
    if not kind:
        return None
    normalized = kind.lower()
    if normalized == "movie":
        return "movie"
    if normalized == "series":
        return "tv"
    return None


def _extract_tmdb_id(provider_ids: Any) -> str | None:
    """Extract a TMDB ID from provider identifiers."""
    if not isinstance(provider_ids, dict):
        return None
    for key, value in provider_ids.items():
        if key.lower() != "tmdb":
            continue
        if value is None:
            return None
        return str(value)
    return None


def _extract_plex_tmdb_id(entry: dict[str, Any]) -> str | None:
    """Extract TMDB IDs from Plex metadata GUIDs."""
    guids = entry.get("Guid") or entry.get("guid")
    if isinstance(guids, list):
        for guid in guids:
            candidate = None
            if isinstance(guid, dict):
                candidate = guid.get("id") or guid.get("Id") or guid.get("guid")
            if candidate:
                match = TMDB_GUID_REGEX.search(str(candidate))
                if match:
                    return match.group("id")
    if isinstance(guids, str):
        match = TMDB_GUID_REGEX.search(guids)
        if match:
            return match.group("id")
    return None


async def _jellyfin_request(
    client: httpx.AsyncClient,
    base_url: str,
    api_key: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
) -> Any:
    """Issue a Jellyfin request with API key credentials."""
    merged_params = dict(params or {})
    merged_params["api_key"] = api_key
    url = f"{base_url}{path}"
    response = await client.get(url, headers=headers, params=merged_params)
    if response.status_code in {401, 403}:
        raise IntegrationSyncError("jellyfin_auth_failed", clear_credentials=True)
    if response.status_code >= 400:
        raise IntegrationSyncError(f"jellyfin_error_{response.status_code}")
    try:
        return response.json()
    except ValueError as exc:
        raise IntegrationSyncError("jellyfin_invalid_response") from exc


async def _plex_request(
    client: httpx.AsyncClient,
    base_url: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
) -> Any:
    """Issue a Plex request with API token credentials."""
    url = f"{base_url}{path}"
    response = await client.get(url, headers=headers, params=params)
    if response.status_code in {401, 403}:
        raise IntegrationSyncError("plex_auth_failed", clear_credentials=True)
    if response.status_code >= 400:
        raise IntegrationSyncError(f"plex_error_{response.status_code}")
    try:
        return response.json()
    except ValueError as exc:
        raise IntegrationSyncError("plex_invalid_response") from exc


def _filter_plex_sections(sections: list[dict[str, Any]], section_hint: str | None) -> list[dict[str, Any]]:
    """Filter Plex sections by key or title when provided."""
    if not section_hint:
        return sections
    normalized_hint = section_hint.strip().casefold()
    filtered: list[dict[str, Any]] = []
    for section in sections:
        key = str(section.get("key") or "").casefold()
        title = str(section.get("title") or "").casefold()
        if normalized_hint in {key, title}:
            filtered.append(section)
    return filtered


async def _note_sync_error(
    session: AsyncSession, *, user_id: uuid.UUID, provider: str, error: str
) -> None:
    """Record the last sync error against stored credentials."""
    credential = await session.scalar(
        select(UserCredential).where(UserCredential.user_id == user_id, UserCredential.provider == provider)
    )
    if not credential:
        return
    credential.last_error = error[:490]
    await session.commit()


async def _clear_sync_error(
    session: AsyncSession, *, user_id: uuid.UUID, provider: str
) -> None:
    """Clear last error after a successful sync."""
    credential = await session.scalar(
        select(UserCredential).where(UserCredential.user_id == user_id, UserCredential.provider == provider)
    )
    if not credential or not credential.last_error:
        return
    credential.last_error = None
    await session.commit()
