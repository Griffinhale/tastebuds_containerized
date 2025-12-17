from __future__ import annotations

from typing import Iterable

import pytest

from app.ingestion.base import BaseConnector, ConnectorResult
from app.models.media import MediaItem, MediaType


class StubConnector(BaseConnector):
    def __init__(self, source_name: str, results: Iterable[ConnectorResult]) -> None:
        self.source_name = source_name
        self._results = [result for result in results]
        self._results_by_id = {result.source_id: result for result in self._results}

    async def search(self, query: str, limit: int = 3) -> list[str]:
        return [result.source_id for result in self._results][:limit]

    async def fetch(self, identifier: str) -> ConnectorResult:
        return self._results_by_id[identifier]


@pytest.mark.asyncio
async def test_search_pagination_produces_metadata(client, session):
    media_titles = [f'Test Series {i}' for i in range(1, 7)]
    for title in media_titles:
        session.add(MediaItem(media_type=MediaType.MOVIE, title=title))
    await session.commit()

    response = await client.get('/api/search', params={'q': 'Test', 'page': 2, 'per_page': 2})
    assert response.status_code == 200
    payload = response.json()
    assert payload['metadata']['paging']['total_internal'] == len(media_titles)
    assert payload['metadata']['counts']['internal'] == 2
    assert payload['metadata']['source_counts']['internal'] == 2
    assert len(payload['results']) == 2
    assert payload['source'] == 'internal'


@pytest.mark.asyncio
async def test_search_external_ingests_multi_source(client, monkeypatch, session):
    session.add(MediaItem(media_type=MediaType.BOOK, title='Fan Query'))
    await session.commit()

    tmdb_results = [
        ConnectorResult(
            media_type=MediaType.MOVIE,
            title='TMDB Pick 1',
            description=None,
            release_date=None,
            cover_image_url=None,
            canonical_url=None,
            metadata={},
            source_name='tmdb',
            source_id='movie:9001',
            raw_payload={},
        ),
        ConnectorResult(
            media_type=MediaType.MOVIE,
            title='TMDB Pick 2',
            description=None,
            release_date=None,
            cover_image_url=None,
            canonical_url=None,
            metadata={},
            source_name='tmdb',
            source_id='movie:9002',
            raw_payload={},
        ),
    ]
    google_results = [
        ConnectorResult(
            media_type=MediaType.BOOK,
            title='Book Find 1',
            description=None,
            release_date=None,
            cover_image_url=None,
            canonical_url=None,
            metadata={},
            source_name='google_books',
            source_id='book:abc',
            raw_payload={},
        )
    ]
    connectors = {
        'google_books': StubConnector('google_books', google_results),
        'tmdb': StubConnector('tmdb', tmdb_results),
        'igdb': StubConnector('igdb', []),
        'lastfm': StubConnector('lastfm', []),
    }

    def _fake_get_connector(source: str) -> BaseConnector:
        try:
            return connectors[source.lower()]
        except KeyError as exc:
            raise ValueError(f'Unsupported source {source}') from exc

    monkeypatch.setattr('app.services.media_service.get_connector', _fake_get_connector)

    response = await client.get(
        '/api/search',
        params={'q': 'Fan', 'include_external': 'true', 'external_per_source': 2},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload['source'] == 'internal+external'
    assert payload['metadata']['counts']['internal'] == 1
    assert payload['metadata']['counts']['external_ingested'] == 3
    assert payload['metadata']['source_counts']['external'] == 3
    assert payload['metadata']['source_counts']['tmdb'] == 2
    assert payload['metadata']['source_counts']['google_books'] == 1
    assert len(payload['results']) >= 4
