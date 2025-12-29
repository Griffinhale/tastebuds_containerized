"""API tests for menu sharing, pairing, and lineage endpoints."""

from __future__ import annotations

import pytest

from app.models.media import MediaItem, MediaType
from app.tests.utils import register_and_login


async def _create_menu_with_items(client, session, *, title: str, is_public: bool):
    media_primary = MediaItem(title="First Item", media_type=MediaType.BOOK)
    media_secondary = MediaItem(title="Second Item", media_type=MediaType.MOVIE)
    session.add_all([media_primary, media_secondary])
    await session.commit()

    menu_res = await client.post(
        "/api/menus",
        json={"title": title, "description": "Testing", "is_public": is_public},
    )
    assert menu_res.status_code == 201
    menu = menu_res.json()

    course_res = await client.post(
        f"/api/menus/{menu['id']}/courses",
        json={"title": "Course", "description": "Test", "position": 1},
    )
    assert course_res.status_code == 201
    course = course_res.json()

    primary_res = await client.post(
        f"/api/menus/{menu['id']}/courses/{course['id']}/items",
        json={"media_item_id": str(media_primary.id), "position": 1},
    )
    assert primary_res.status_code == 201
    paired_res = await client.post(
        f"/api/menus/{menu['id']}/courses/{course['id']}/items",
        json={"media_item_id": str(media_secondary.id), "position": 2},
    )
    assert paired_res.status_code == 201

    return {
        "menu": menu,
        "course": course,
        "primary_item_id": primary_res.json()["id"],
        "paired_item_id": paired_res.json()["id"],
    }


@pytest.mark.asyncio
async def test_menu_share_tokens_and_public_draft(client, session):
    await register_and_login(client, prefix="share")

    created = await _create_menu_with_items(client, session, title="Draft Menu", is_public=False)
    menu_id = created["menu"]["id"]

    token_res = await client.post(f"/api/menus/{menu_id}/share-tokens", json={})
    assert token_res.status_code == 201
    token_payload = token_res.json()

    list_res = await client.get(f"/api/menus/{menu_id}/share-tokens")
    assert list_res.status_code == 200
    assert token_payload["id"] in {item["id"] for item in list_res.json()}

    draft_res = await client.get(f"/api/public/menus/draft/{token_payload['token']}")
    assert draft_res.status_code == 200
    draft_payload = draft_res.json()
    assert draft_payload["menu"]["id"] == menu_id
    assert draft_payload["share_token_id"] == token_payload["id"]

    revoke_res = await client.delete(f"/api/menus/{menu_id}/share-tokens/{token_payload['id']}")
    assert revoke_res.status_code == 204

    revoked_res = await client.get(f"/api/public/menus/draft/{token_payload['token']}")
    assert revoked_res.status_code == 404


@pytest.mark.asyncio
async def test_menu_pairings_and_lineage(client, session):
    await register_and_login(client, prefix="lineage")

    created = await _create_menu_with_items(client, session, title="Source Menu", is_public=True)
    menu = created["menu"]

    pairing_res = await client.post(
        f"/api/menus/{menu['id']}/pairings",
        json={
            "primary_course_item_id": created["primary_item_id"],
            "paired_course_item_id": created["paired_item_id"],
            "relationship": "echo",
            "note": "Pairs nicely",
        },
    )
    assert pairing_res.status_code == 201

    list_res = await client.get(f"/api/menus/{menu['id']}/pairings")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    delete_res = await client.delete(
        f"/api/menus/{menu['id']}/pairings/{pairing_res.json()['id']}"
    )
    assert delete_res.status_code == 204

    list_res = await client.get(f"/api/menus/{menu['id']}/pairings")
    assert list_res.status_code == 200
    assert list_res.json() == []

    fork_res = await client.post(
        f"/api/menus/{menu['id']}/fork",
        json={"title": "Forked Menu", "is_public": True, "note": "Remix"},
    )
    assert fork_res.status_code == 201
    forked = fork_res.json()

    lineage_res = await client.get(f"/api/menus/{forked['id']}/lineage")
    assert lineage_res.status_code == 200
    lineage = lineage_res.json()
    assert lineage["source_menu"]["menu"]["id"] == menu["id"]

    public_lineage = await client.get(f"/api/public/menus/{menu['slug']}/lineage")
    assert public_lineage.status_code == 200
    public_payload = public_lineage.json()
    assert public_payload["fork_count"] == 1
    assert forked["id"] in {item["id"] for item in public_payload["forked_menus"]}
