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


@pytest.mark.asyncio
async def test_reorder_course_items(client, session):
    creds = _auth_payload()
    await client.post("/api/auth/register", json=creds)
    await client.post("/api/auth/login", json={"email": creds["email"], "password": creds["password"]})

    menu_res = await client.post(
        "/api/menus",
        json={"title": "Sample Menu", "description": "Two items", "is_public": True},
    )
    assert menu_res.status_code == 201
    menu_id = menu_res.json()["id"]

    course_res = await client.post(
        f"/api/menus/{menu_id}/courses",
        json={"title": "Course", "description": "Testing reorder", "position": 1},
    )
    assert course_res.status_code == 201
    course = course_res.json()

    first_media = MediaItem(title="First", media_type=MediaType.BOOK)
    second_media = MediaItem(title="Second", media_type=MediaType.MOVIE)
    session.add_all([first_media, second_media])
    await session.commit()

    first_item = await client.post(
        f"/api/menus/{menu_id}/courses/{course['id']}/items",
        json={"media_item_id": str(first_media.id), "position": 1},
    )
    assert first_item.status_code == 201
    second_item = await client.post(
        f"/api/menus/{menu_id}/courses/{course['id']}/items",
        json={"media_item_id": str(second_media.id), "position": 2},
    )
    assert second_item.status_code == 201

    first = first_item.json()
    second = second_item.json()

    reorder_res = await client.post(
        f"/api/menus/{menu_id}/courses/{course['id']}/reorder-items",
        json={"item_ids": [second["id"], first["id"]]},
    )
    assert reorder_res.status_code == 200
    reordered = reorder_res.json()
    assert [item["id"] for item in reordered["items"]] == [second["id"], first["id"]]
