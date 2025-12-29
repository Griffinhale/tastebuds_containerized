"""API tests for taste profile aggregation."""

from __future__ import annotations

import pytest

from app.models.media import MediaItem, MediaType
from app.tests.utils import register_and_login


@pytest.mark.asyncio
async def test_taste_profile_builds_from_logs_tags_and_menus(client, session):
    await register_and_login(client, prefix="taste")

    book = MediaItem(title="Taste Book", media_type=MediaType.BOOK)
    movie = MediaItem(title="Taste Movie", media_type=MediaType.MOVIE)
    session.add_all([book, movie])
    await session.commit()

    menu_res = await client.post(
        "/api/menus",
        json={
            "title": "Profile Menu",
            "description": "For taste profile",
            "is_public": False,
            "courses": [
                {
                    "title": "Course",
                    "position": 1,
                    "items": [
                        {"media_item_id": str(book.id), "position": 1},
                        {"media_item_id": str(movie.id), "position": 2},
                    ],
                }
            ],
        },
    )
    assert menu_res.status_code == 201

    tag_res = await client.post("/api/tags", json={"name": "Noir"})
    assert tag_res.status_code == 201
    tag_id = tag_res.json()["id"]
    attach_res = await client.post(
        f"/api/tags/{tag_id}/media",
        json={"media_item_id": str(book.id)},
    )
    assert attach_res.status_code == 201

    log_res = await client.post(
        "/api/me/logs",
        json={"media_item_id": str(book.id), "log_type": "finished"},
    )
    assert log_res.status_code == 201

    profile_res = await client.get("/api/me/taste-profile")
    assert profile_res.status_code == 200
    profile = profile_res.json()["profile"]

    assert profile["summary"]["menus"] == 1
    assert profile["summary"]["courses"] == 1
    assert profile["summary"]["items"] == 2
    assert profile["media_type_counts"]["book"] == 1
    assert profile["media_type_counts"]["movie"] == 1
    assert profile["log_counts"]["finished"] == 1
    assert profile["signals"]["media_items"] == 2

    refresh_res = await client.post("/api/me/taste-profile/refresh", json={"force": True})
    assert refresh_res.status_code == 200
