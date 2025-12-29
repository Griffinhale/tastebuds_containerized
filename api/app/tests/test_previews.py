"""Tests for external preview detail access control and expiry."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

import pytest

from app.models.media import MediaType
from app.models.search_preview import ExternalSearchPreview
from app.tests.utils import register_and_login


@pytest.mark.asyncio
async def test_preview_detail_scoped_and_expires(client, session):
    auth = await register_and_login(client, prefix="preview")

    preview = ExternalSearchPreview(
        user_id=uuid.UUID(auth.user["id"]),
        source_name="tmdb",
        external_id="movie:123",
        media_type=MediaType.MOVIE,
        title="Preview Film",
        description="Preview description",
        release_date=None,
        cover_image_url=None,
        canonical_url="https://example.com/title",
        metadata_payload={"genres": ["sci-fi"]},
        raw_payload={
            "source_url": "https://tmdb.org/title/123",
            "extensions": {"movie": {"runtime_minutes": 117}},
        },
        expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
    )
    session.add(preview)
    await session.commit()

    detail_res = await client.get(f"/api/previews/{preview.id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["preview_id"] == str(preview.id)
    assert detail["source_id"] == "movie:123"
    assert detail["source_url"] == "https://tmdb.org/title/123"
    assert detail["movie"]["runtime_minutes"] == 117

    await register_and_login(client, prefix="other")
    blocked_res = await client.get(f"/api/previews/{preview.id}")
    assert blocked_res.status_code == 404

    await client.post("/api/auth/login", json={"email": auth.email, "password": auth.password})
    preview.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    await session.commit()

    expired_res = await client.get(f"/api/previews/{preview.id}")
    assert expired_res.status_code == 404
