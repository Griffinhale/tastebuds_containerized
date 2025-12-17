from __future__ import annotations

import uuid

import pytest

from app.models.media import MediaItem, MediaType


def _auth_payload():
    suffix = uuid.uuid4().hex[:6]
    return {
        "email": f"menu_{suffix}@example.com",
        "password": "supersecret123",
        "display_name": f"Menu Tester {suffix}",
    }


@pytest.mark.asyncio
async def test_menu_course_item_flow(client, session):
    creds = _auth_payload()
    await client.post("/api/auth/register", json=creds)
    await client.post("/api/auth/login", json={"email": creds["email"], "password": creds["password"]})

    menu_res = await client.post(
        "/api/menus",
        json={"title": "Evening Pairings", "description": "Books & films", "is_public": True},
    )
    assert menu_res.status_code == 201
    menu = menu_res.json()
    menu_id = menu["id"]

    course_res = await client.post(
        f"/api/menus/{menu_id}/courses",
        json={"title": "Appetizer", "description": "Openers", "position": 1},
    )
    assert course_res.status_code == 201
    course = course_res.json()

    media = MediaItem(title="Blade Runner", media_type=MediaType.MOVIE)
    session.add(media)
    await session.commit()

    item_res = await client.post(
        f"/api/menus/{menu_id}/courses/{course['id']}/items",
        json={
            "media_item_id": str(media.id),
            "position": 1,
            "notes": "Watch before reading.",
        },
    )
    assert item_res.status_code == 201
    item = item_res.json()
    assert item["media_item_id"] == str(media.id)

    list_res = await client.get("/api/menus")
    assert list_res.status_code == 200
    menus = list_res.json()
    assert len(menus) == 1
    assert menus[0]["courses"][0]["items"][0]["id"] == item["id"]

    delete_item_res = await client.delete(f"/api/menus/{menu_id}/course-items/{item['id']}")
    assert delete_item_res.status_code == 204

    delete_course_res = await client.delete(f"/api/menus/{menu_id}/courses/{course['id']}")
    assert delete_course_res.status_code == 204

    detail_res = await client.get(f"/api/menus/{menu_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["courses"] == []
