from __future__ import annotations

import uuid

import pytest

from app.core.config import settings


async def _authenticate_health_user(client):
    suffix = uuid.uuid4().hex[:8]
    creds = {
        "email": f"health_{suffix}@example.com",
        "password": "healthpass123",
        "display_name": f"Health Tester {suffix}",
    }
    res = await client.post("/api/auth/register", json=creds)
    assert res.status_code == 200
    login_res = await client.post(
        "/api/auth/login",
        json={"email": creds["email"], "password": creds["password"]},
    )
    assert login_res.status_code == 200


@pytest.mark.asyncio
async def test_health_reports_ok_without_auth(client, monkeypatch):
    called = False

    async def _snapshot_stub() -> dict[str, object]:
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr("app.main.ingestion_monitor.snapshot", _snapshot_stub)

    response = await client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "ingestion" not in payload
    assert called is False


@pytest.mark.asyncio
async def test_health_reports_ok_for_authenticated_users(client, monkeypatch):
    async def _snapshot_stub() -> dict[str, object]:
        return {}

    monkeypatch.setattr("app.main.ingestion_monitor.snapshot", _snapshot_stub)
    await _authenticate_health_user(client)

    response = await client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["ingestion"]["sources"] == {}
    assert payload["ingestion"]["issues"] == []


@pytest.mark.asyncio
async def test_health_degrades_for_authenticated_users(client, monkeypatch):
    async def _snapshot_stub() -> dict[str, object]:
        return {
            "tmdb": {
                "circuit": {
                    "failure_streak": 0,
                    "open_until": 0.0,
                    "remaining_cooldown": 12.25,
                    "current_backoff": 30.0,
                    "opened_count": 1,
                },
                "operations": {
                    "fetch": {
                        "started": 2,
                        "succeeded": 1,
                        "failed": 1,
                        "skipped": 0,
                        "last_latency_ms": 220.13,
                        "last_error": "quota exceeded",
                    }
                },
            }
        }

    monkeypatch.setattr("app.main.ingestion_monitor.snapshot", _snapshot_stub)
    await _authenticate_health_user(client)

    response = await client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    telemetry = payload["ingestion"]
    assert telemetry["sources"]["tmdb"]["operations"]["fetch"]["last_error"] == "quota exceeded"
    assert telemetry["sources"]["tmdb"]["state"] == "degraded"
    assert telemetry["issues"][0]["source"] == "tmdb"
    assert telemetry["issues"][0]["reason"] in {"circuit_open", "last_error"}


@pytest.mark.asyncio
async def test_health_allows_allowlisted_clients_without_auth(client, monkeypatch):
    async def _snapshot_stub() -> dict[str, object]:
        return {}

    monkeypatch.setattr("app.main.ingestion_monitor.snapshot", _snapshot_stub)
    monkeypatch.setattr(settings, "health_allowlist", ["testserver"])

    response = await client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["ingestion"]["issues"] == []


@pytest.mark.asyncio
async def test_health_flags_repeated_failures(client, monkeypatch):
    async def _snapshot_stub() -> dict[str, object]:
        return {
            "lastfm": {
                "circuit": {
                    "failure_streak": 0,
                    "open_until": 0.0,
                    "remaining_cooldown": 0.0,
                    "current_backoff": 30.0,
                    "opened_count": 0,
                },
                "operations": {
                    "search": {
                        "started": 3,
                        "succeeded": 0,
                        "failed": 3,
                        "skipped": 0,
                        "last_latency_ms": 120.0,
                        "last_error": None,
                    }
                },
            }
        }

    monkeypatch.setattr("app.main.ingestion_monitor.snapshot", _snapshot_stub)
    await _authenticate_health_user(client)

    response = await client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    issues = payload["ingestion"]["issues"]
    assert any(issue["reason"] == "repeated_failures" for issue in issues)
    assert payload["ingestion"]["sources"]["lastfm"]["state"] == "degraded"
