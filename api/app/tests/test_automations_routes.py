"""API tests for automation rule lifecycle."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.tests.utils import register_and_login


@pytest.mark.asyncio
async def test_automation_rule_lifecycle(client, monkeypatch):
    await register_and_login(client, prefix="automation")

    async def fake_ingest(session, *, source, identifier, force_refresh=False):
        return SimpleNamespace(id=uuid.uuid4())

    from app.services import automation_engine

    monkeypatch.setattr(automation_engine.media_service, "ingest_from_source", fake_ingest)

    create_res = await client.post(
        "/api/automations",
        json={
            "name": "Morning ingest",
            "description": "Kick off daily ingest",
            "enabled": True,
            "trigger_type": "schedule",
            "trigger_config": {"cron": "0 9 * * *"},
            "action_type": "ingest",
            "action_config": {"source": "tmdb", "identifier": "movie:603"},
        },
    )
    assert create_res.status_code == 201
    rule = create_res.json()
    assert rule["trigger_type"] == "schedule"

    list_res = await client.get("/api/automations")
    assert list_res.status_code == 200
    assert rule["id"] in {item["id"] for item in list_res.json()}

    update_res = await client.patch(
        f"/api/automations/{rule['id']}",
        json={"enabled": False, "description": "Paused"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["enabled"] is False

    run_res = await client.post(f"/api/automations/{rule['id']}/run")
    assert run_res.status_code == 200
    run_payload = run_res.json()
    assert run_payload["status"] == "completed"
    assert run_payload["detail"]["action_type"] == "ingest"
    assert run_payload["detail"]["action_status"] == "ingested"
    assert run_payload["detail"]["action_result"]["media_item_id"]

    delete_res = await client.delete(f"/api/automations/{rule['id']}")
    assert delete_res.status_code == 204


@pytest.mark.asyncio
async def test_automation_rule_sync_action(client, monkeypatch):
    await register_and_login(client, prefix="automation_sync")

    async def fake_process_sync(session, task):
        return {
            "status": "synced",
            "provider": task.provider,
            "external_id": task.external_id,
        }

    from app.services import automation_engine

    monkeypatch.setattr(automation_engine.sync_service, "process_sync_task", fake_process_sync)

    create_res = await client.post(
        "/api/automations",
        json={
            "name": "Nightly sync",
            "description": "Refresh Jellyfin catalog",
            "enabled": True,
            "trigger_type": "schedule",
            "trigger_config": {"cron": "0 2 * * *"},
            "action_type": "sync",
            "action_config": {"provider": "jellyfin"},
        },
    )
    assert create_res.status_code == 201
    rule = create_res.json()

    run_res = await client.post(f"/api/automations/{rule['id']}/run")
    assert run_res.status_code == 200
    run_payload = run_res.json()
    assert run_payload["status"] == "completed"
    assert run_payload["detail"]["action_type"] == "sync"
    assert run_payload["detail"]["action_status"] == "synced"
    assert run_payload["detail"]["action_result"]["external_id"] == "library"
