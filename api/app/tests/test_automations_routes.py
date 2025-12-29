"""API tests for automation rule lifecycle."""

from __future__ import annotations

import pytest

from app.tests.utils import register_and_login


@pytest.mark.asyncio
async def test_automation_rule_lifecycle(client):
    await register_and_login(client, prefix="automation")

    create_res = await client.post(
        "/api/automations",
        json={
            "name": "Morning ingest",
            "description": "Kick off daily ingest",
            "enabled": True,
            "trigger_type": "schedule",
            "trigger_config": {"cron": "0 9 * * *"},
            "action_type": "ingest",
            "action_config": {"source": "tmdb"},
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
    assert run_payload["status"] == "queued"
    assert run_payload["detail"]["status"] == "queued"

    delete_res = await client.delete(f"/api/automations/{rule['id']}")
    assert delete_res.status_code == 204
