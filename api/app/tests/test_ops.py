"""Tests for ops endpoints and admin-only access checks."""

from __future__ import annotations

import uuid

import pytest

from app.core.config import settings


def _auth_payload() -> dict[str, str]:
    suffix = uuid.uuid4().hex[:6]
    return {
        "email": f"ops_{suffix}@example.com",
        "password": "supersecret123",
        "display_name": f"Ops {suffix}",
    }


@pytest.mark.asyncio
async def test_ops_requires_auth(client):
    response = await client.get("/api/ops/queues")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_ops_snapshot_with_auth(client):
    creds = _auth_payload()
    await client.post("/api/auth/register", json=creds)
    await client.post("/api/auth/login", json={"email": creds["email"], "password": creds["password"]})
    settings.ops_admin_emails = [creds["email"]]

    response = await client.get("/api/ops/queues")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "queues" in data
    assert "vault" in data
