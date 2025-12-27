"""Authentication route tests for register/login/refresh/logout flows."""

from __future__ import annotations

import uuid

import pytest


def _make_credentials():
    suffix = uuid.uuid4().hex[:8]
    return {
        "email": f"tester_{suffix}@example.com",
        "password": "safepassword123",
        "display_name": f"Tester {suffix}",
    }


@pytest.mark.asyncio
async def test_register_and_login_flow(client):
    creds = _make_credentials()

    register_res = await client.post("/api/auth/register", json=creds)
    assert register_res.status_code == 200
    register_body = register_res.json()
    assert register_body["user"]["email"] == creds["email"]
    assert register_body["access_token"]
    assert register_res.cookies.get("access_token")
    assert register_res.cookies.get("refresh_token")

    login_res = await client.post(
        "/api/auth/login",
        json={"email": creds["email"], "password": creds["password"]},
    )
    assert login_res.status_code == 200
    login_body = login_res.json()
    assert login_body["user"]["email"] == creds["email"]
    assert login_res.cookies.get("access_token")


@pytest.mark.asyncio
async def test_refresh_and_logout_flow(client):
    creds = _make_credentials()
    await client.post("/api/auth/register", json=creds)
    await client.post("/api/auth/login", json={"email": creds["email"], "password": creds["password"]})

    original_refresh = client.cookies.get("refresh_token")
    assert original_refresh

    refresh_res = await client.post("/api/auth/refresh")
    assert refresh_res.status_code == 200
    refresh_body = refresh_res.json()
    assert refresh_body["user"]["email"] == creds["email"]
    assert refresh_res.cookies.get("access_token")
    rotated_refresh = refresh_res.cookies.get("refresh_token")
    assert rotated_refresh
    assert rotated_refresh != original_refresh

    # Reusing the old token should now fail
    # API cookies are host-only, so override without specifying a domain.
    client.cookies.set("refresh_token", original_refresh, path="/")
    reuse_res = await client.post("/api/auth/refresh")
    assert reuse_res.status_code == 401

    logout_res = await client.post("/api/auth/logout")
    assert logout_res.status_code == 204
    assert logout_res.cookies.get("access_token") == ""
    assert logout_res.cookies.get("refresh_token") == ""

    # The rotated refresh token is now revoked as well
    client.cookies.set("refresh_token", rotated_refresh, path="/")
    post_logout_refresh = await client.post("/api/auth/refresh")
    assert post_logout_refresh.status_code == 401
