"""API tests for integration status and credential management."""

from __future__ import annotations

import pytest

from app.tests.utils import register_and_login


@pytest.mark.asyncio
async def test_integration_status_and_webhook_token(client):
    await register_and_login(client, prefix="integrations")

    status_res = await client.get("/api/integrations")
    assert status_res.status_code == 200
    status_map = {item["provider"]: item for item in status_res.json()}
    assert status_map["arr"]["connected"] is False

    store_res = await client.post(
        "/api/integrations/arr/credentials",
        json={"payload": {"api_key": "secret"}},
    )
    assert store_res.status_code == 200
    assert store_res.json()["status"] == "connected"

    token_res = await client.post("/api/integrations/arr/webhook-token")
    assert token_res.status_code == 200
    token_payload = token_res.json()
    assert token_payload["provider"] == "arr"
    assert token_payload["token_prefix"]
    assert "/api/integrations/arr/webhook/" in token_payload["webhook_url"]

    status_res = await client.get("/api/integrations")
    status_map = {item["provider"]: item for item in status_res.json()}
    assert status_map["arr"]["webhook_token_prefix"] == token_payload["token_prefix"]

    delete_res = await client.delete("/api/integrations/arr")
    assert delete_res.status_code == 204

    status_res = await client.get("/api/integrations")
    status_map = {item["provider"]: item for item in status_res.json()}
    assert status_map["arr"]["connected"] is False
    assert status_map["arr"]["webhook_token_prefix"] is None
