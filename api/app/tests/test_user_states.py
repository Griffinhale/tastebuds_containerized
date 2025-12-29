"""API tests for user state endpoints."""

from __future__ import annotations

import pytest

from app.models.media import MediaItem, MediaType
from app.tests.utils import register_and_login


@pytest.mark.asyncio
async def test_user_state_upsert_and_list(client, session):
    await register_and_login(client, prefix="state")

    media = MediaItem(title="State Book", media_type=MediaType.BOOK)
    session.add(media)
    await session.commit()

    upsert_res = await client.put(
        f"/api/me/states/{media.id}",
        json={"status": "currently_consuming", "rating": 8, "favorite": True},
    )
    assert upsert_res.status_code == 200
    payload = upsert_res.json()
    assert payload["media_item_id"] == str(media.id)
    assert payload["rating"] == 8

    list_res = await client.get("/api/me/states")
    assert list_res.status_code == 200
    states = list_res.json()
    assert len(states) == 1

    update_res = await client.put(
        f"/api/me/states/{media.id}",
        json={"status": "consumed", "rating": 9, "favorite": False},
    )
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "consumed"
