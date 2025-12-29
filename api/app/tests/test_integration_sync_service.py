"""Integration sync adapter tests."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.services import integration_service, integration_sync_service
from app.services.sync_service import SyncTask
from app.tests.utils import register_and_login


@pytest.mark.asyncio
async def test_jellyfin_sync_ingests_tmdb_items(session, client, monkeypatch):
    auth = await register_and_login(client, prefix="jellyfin")
    user_id = uuid.UUID(auth.user_id)
    await integration_service.store_credentials(
        session,
        user_id=user_id,
        provider="jellyfin",
        payload={"base_url": "https://jellyfin.local", "api_key": "secret"},
    )

    scan = integration_sync_service.ScanResult(
        items=[
            integration_sync_service.SyncItem(tmdb_id="603", media_kind="movie", title="The Matrix"),
            integration_sync_service.SyncItem(tmdb_id="1399", media_kind="tv", title="Game of Thrones"),
        ],
        scanned=2,
    )

    async def fake_scan(*, base_url, api_key, library_id):
        return scan

    calls: list[tuple[str, str, bool]] = []

    async def fake_ingest(session, *, source, identifier, force_refresh=False):
        calls.append((source, identifier, force_refresh))
        return SimpleNamespace(id=uuid.uuid4())

    monkeypatch.setattr(integration_sync_service, "_scan_jellyfin_library", fake_scan)
    monkeypatch.setattr(integration_sync_service.media_service, "ingest_from_source", fake_ingest)

    task = SyncTask(
        provider="jellyfin",
        external_id="library",
        action="sync",
        force_refresh=False,
        requested_by=user_id,
    )
    result = await integration_sync_service.process_integration_sync(session, task)

    assert result["status"] == "synced"
    assert result["ingested"] == 2
    assert ("tmdb", "movie:603", False) in calls
    assert ("tmdb", "tv:1399", False) in calls


@pytest.mark.asyncio
async def test_plex_sync_ingests_tmdb_items(session, client, monkeypatch):
    auth = await register_and_login(client, prefix="plex")
    user_id = uuid.UUID(auth.user_id)
    await integration_service.store_credentials(
        session,
        user_id=user_id,
        provider="plex",
        payload={"base_url": "https://plex.local", "api_key": "secret"},
    )

    scan = integration_sync_service.ScanResult(
        items=[
            integration_sync_service.SyncItem(tmdb_id="603", media_kind="movie", title="The Matrix"),
        ],
        scanned=1,
    )

    async def fake_scan(*, base_url, token, section_hint):
        return scan

    calls: list[tuple[str, str, bool]] = []

    async def fake_ingest(session, *, source, identifier, force_refresh=False):
        calls.append((source, identifier, force_refresh))
        return SimpleNamespace(id=uuid.uuid4())

    monkeypatch.setattr(integration_sync_service, "_scan_plex_library", fake_scan)
    monkeypatch.setattr(integration_sync_service.media_service, "ingest_from_source", fake_ingest)

    task = SyncTask(
        provider="plex",
        external_id="library",
        action="sync",
        force_refresh=False,
        requested_by=user_id,
    )
    result = await integration_sync_service.process_integration_sync(session, task)

    assert result["status"] == "synced"
    assert result["ingested"] == 1
    assert ("tmdb", "movie:603", False) in calls
