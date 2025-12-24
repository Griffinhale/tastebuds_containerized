from __future__ import annotations

import uuid

import pytest


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
    async def _snapshot_stub() -> dict[str, object]:
        return {}

    monkeypatch.setattr("app.main.ingestion_monitor.snapshot", _snapshot_stub)

    response = await client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "ingestion" not in payload


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
    assert telemetry["issues"][0]["source"] == "tmdb"
    assert telemetry["issues"][0]["reason"] in {"circuit_open", "last_error"}
