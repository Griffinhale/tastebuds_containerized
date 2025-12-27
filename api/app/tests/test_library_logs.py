"""API tests for library and log endpoints."""

from __future__ import annotations

import uuid

import pytest

from app.models.media import MediaItem, MediaType


def _auth_payload():
    suffix = uuid.uuid4().hex[:6]
    return {
        "email": f"library_{suffix}@example.com",
        "password": "supersecret123",
        "display_name": f"Library Tester {suffix}",
    }


@pytest.mark.asyncio
async def test_log_flow_updates_library(client, session):
    creds = _auth_payload()
    await client.post("/api/auth/register", json=creds)
    await client.post("/api/auth/login", json={"email": creds["email"], "password": creds["password"]})

    media = MediaItem(title="Log Book", media_type=MediaType.BOOK)
    session.add(media)
    await session.commit()

    create_log = await client.post(
        "/api/me/logs",
        json={
            "media_item_id": str(media.id),
            "log_type": "started",
            "notes": "First session",
            "minutes_spent": 30,
        },
    )
    assert create_log.status_code == 201

    library_res = await client.get("/api/me/library")
    assert library_res.status_code == 200
    library = library_res.json()
    assert library["summary"]["currently_consuming"] == 1
    assert library["items"][0]["log_count"] == 1
    assert library["next_up"][0]["media_item"]["id"] == str(media.id)

    finish_log = await client.post(
        "/api/me/logs",
        json={
            "media_item_id": str(media.id),
            "log_type": "finished",
            "notes": "Done",
        },
    )
    assert finish_log.status_code == 201

    state_res = await client.get("/api/me/states")
    assert state_res.status_code == 200
    state = state_res.json()[0]
    assert state["status"] == "consumed"


@pytest.mark.asyncio
async def test_log_filters_and_update(client, session):
    creds = _auth_payload()
    await client.post("/api/auth/register", json=creds)
    await client.post("/api/auth/login", json={"email": creds["email"], "password": creds["password"]})

    media = MediaItem(title="Progress Title", media_type=MediaType.MOVIE)
    session.add(media)
    await session.commit()

    note_log = await client.post(
        "/api/me/logs",
        json={
            "media_item_id": str(media.id),
            "log_type": "note",
            "notes": "Initial note",
        },
    )
    assert note_log.status_code == 201
    log_id = note_log.json()["id"]

    update_log = await client.patch(
        f"/api/me/logs/{log_id}",
        json={
            "log_type": "progress",
            "progress_percent": 40,
            "notes": "Updated note",
        },
    )
    assert update_log.status_code == 200
    updated = update_log.json()
    assert updated["log_type"] == "progress"
    assert updated["progress_percent"] == 40

    filtered = await client.get(f"/api/me/logs?log_type=progress&media_item_id={media.id}")
    assert filtered.status_code == 200
    logs = filtered.json()
    assert len(logs) == 1
    assert logs[0]["id"] == log_id
