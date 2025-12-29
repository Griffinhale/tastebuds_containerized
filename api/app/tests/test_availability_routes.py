"""API tests for availability endpoints and summaries."""

from __future__ import annotations

import pytest

from app.models.media import MediaItem, MediaType
from app.tests.utils import register_and_login


@pytest.mark.asyncio
async def test_availability_upsert_and_summary(client, session):
    await register_and_login(client, prefix="availability")

    media = MediaItem(title="Availability Title", media_type=MediaType.MOVIE)
    session.add(media)
    await session.commit()

    list_res = await client.get(f"/api/media/{media.id}/availability")
    assert list_res.status_code == 200
    assert list_res.json() == []

    upsert_payload = [
        {
            "provider": "netflix",
            "region": "US",
            "format": "stream",
            "status": "available",
            "deeplink_url": "https://netflix.example/title",
        },
        {
            "provider": "criterion",
            "region": "US",
            "format": "rent",
            "status": "unavailable",
        },
    ]
    upsert_res = await client.put(
        f"/api/media/{media.id}/availability",
        json=upsert_payload,
    )
    assert upsert_res.status_code == 200
    entries = upsert_res.json()
    assert {entry["provider"] for entry in entries} == {"netflix", "criterion"}

    summary_res = await client.post(
        "/api/media/availability/summary",
        json={"media_item_ids": [str(media.id)]},
    )
    assert summary_res.status_code == 200
    summary = summary_res.json()[0]
    assert summary["media_item_id"] == str(media.id)
    assert set(summary["providers"]) == {"netflix", "criterion"}
    assert set(summary["regions"]) == {"US"}
    assert summary["status_counts"]["available"] == 1
    assert summary["status_counts"]["unavailable"] == 1
