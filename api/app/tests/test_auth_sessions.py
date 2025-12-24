from __future__ import annotations

import uuid

import pytest


def _creds(prefix: str) -> dict[str, str]:
    return {
        "email": f"{prefix}_{uuid.uuid4().hex[:8]}@example.com",
        "password": "sessionpass123",
        "display_name": f"{prefix.title()} User",
    }


@pytest.mark.asyncio
async def test_session_inventory_and_revoke(client):
    res = await client.post("/api/auth/register", json=_creds("primary"))
    assert res.status_code == 200

    listing = await client.get("/api/auth/sessions")
    assert listing.status_code == 200
    sessions = listing.json()
    assert sessions
    session_id = sessions[0]["id"]
    assert sessions[0]["is_current"] is True
    assert sessions[0]["is_active"] is True

    revoke_res = await client.post(f"/api/auth/sessions/{session_id}/revoke")
    assert revoke_res.status_code == 204

    after = await client.get("/api/auth/sessions", params={"include_revoked": "true"})
    assert after.status_code == 200
    revoked_session = next(item for item in after.json() if item["id"] == session_id)
    assert revoked_session["is_active"] is False
    assert revoked_session["revoked_at"] is not None


@pytest.mark.asyncio
async def test_session_revoke_is_scoped_to_owner(client):
    res = await client.post("/api/auth/register", json=_creds("owner"))
    assert res.status_code == 200
    owner_sessions = await client.get("/api/auth/sessions")
    owner_session_id = owner_sessions.json()[0]["id"]

    other_res = await client.post("/api/auth/register", json=_creds("other"))
    assert other_res.status_code == 200

    forbidden = await client.post(f"/api/auth/sessions/{owner_session_id}/revoke")
    assert forbidden.status_code == 404
