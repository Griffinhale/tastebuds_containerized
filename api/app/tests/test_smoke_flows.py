"""End-to-end smoke tests for core auth, menu, and ingestion flows."""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.ingestion.base import BaseConnector, ConnectorResult
from app.models.media import MediaType


class SmokeTestConnector(BaseConnector):
    def __init__(self, result: ConnectorResult) -> None:
        self.source_name = result.source_name
        self._result = result

    async def search(self, query: str, limit: int = 3) -> list[str]:
        return [self._result.source_id]

    async def fetch(self, identifier: str) -> ConnectorResult:
        return self._result


def _credentials() -> dict[str, str]:
    suffix = uuid.uuid4().hex[:6]
    return {
        "email": f"smoke_{suffix}@example.com",
        "password": "menusample123",
        "display_name": f"Smoke Tester {suffix}",
    }


@pytest.mark.asyncio
async def test_login_menu_crud_and_search_ingest_flow(client, monkeypatch):
    connector_result = ConnectorResult(
        media_type=MediaType.MOVIE,
        title="Signal Runner",
        description="Synth-forward sci-fi heist.",
        release_date=date(2024, 5, 4),
        cover_image_url=None,
        canonical_url="https://tmdb.test/movie/42",
        metadata={"genres": ["Sci-Fi"]},
        source_name="tmdb",
        source_id="movie:42",
        source_url="https://api.tmdb.org/3/movie/42",
        raw_payload={"id": 42},
        extensions={"movie": {"runtime_minutes": 128}},
    )
    connectors = {"tmdb": SmokeTestConnector(connector_result)}

    def _get_connector(source: str) -> BaseConnector:
        key = source.lower()
        if key not in connectors:
            raise ValueError(f"Unexpected connector {source}")
        return connectors[key]

    monkeypatch.setattr("app.services.media_service.get_connector", _get_connector)

    creds = _credentials()
    register_res = await client.post("/api/auth/register", json=creds)
    assert register_res.status_code == 200
    login_res = await client.post("/api/auth/login", json={"email": creds["email"], "password": creds["password"]})
    assert login_res.status_code == 200

    menu_res = await client.post(
        "/api/menus",
        json={"title": "Evening Signals", "description": "Sci-fi sampler", "is_public": False},
    )
    assert menu_res.status_code == 201
    menu = menu_res.json()
    menu_id = menu["id"]

    course_res = await client.post(
        f"/api/menus/{menu_id}/courses",
        json={"title": "Pilot", "description": "Kickoff picks", "position": 1},
    )
    assert course_res.status_code == 201
    course = course_res.json()

    search_res = await client.get(
        "/api/search",
        params=[("q", "signal"), ("sources", "tmdb"), ("external_per_source", "1")],
    )
    assert search_res.status_code == 200
    search_payload = search_res.json()
    assert search_payload["source"] == "external"
    assert search_payload["metadata"]["counts"]["external_ingested"] == 1
    search_item_id = search_payload["results"][0]["id"]

    add_item_res = await client.post(
        f"/api/menus/{menu_id}/courses/{course['id']}/items",
        json={"media_item_id": search_item_id, "position": 1, "notes": "Pair with vinyl."},
    )
    assert add_item_res.status_code == 201
    course_item = add_item_res.json()
    assert course_item["media_item_id"] != search_item_id

    list_res = await client.get("/api/menus")
    assert list_res.status_code == 200
    menus = list_res.json()
    assert menus[0]["courses"][0]["items"][0]["id"] == course_item["id"]

    delete_item_res = await client.delete(f"/api/menus/{menu_id}/course-items/{course_item['id']}")
    assert delete_item_res.status_code == 204
    delete_course_res = await client.delete(f"/api/menus/{menu_id}/courses/{course['id']}")
    assert delete_course_res.status_code == 204
    delete_menu_res = await client.delete(f"/api/menus/{menu_id}")
    assert delete_menu_res.status_code == 204

    final_list = await client.get("/api/menus")
    assert final_list.status_code == 200
    assert final_list.json() == []
