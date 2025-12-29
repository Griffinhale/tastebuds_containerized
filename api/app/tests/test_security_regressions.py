"""Security regression tests for policy invariants."""

from __future__ import annotations

import pytest

from app.api.routes import search as search_routes


@pytest.mark.asyncio
async def test_external_fanout_not_triggered_without_auth(client, monkeypatch):
    called = False

    async def _fake_enqueue(*args, **kwargs):
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(search_routes.task_queue, "enqueue_or_run", _fake_enqueue)

    response = await client.get(
        "/api/search",
        params=[("q", "anon"), ("include_external", "true")],
    )
    assert response.status_code == 401
    assert called is False
