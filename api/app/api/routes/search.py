from __future__ import annotations

import enum
from typing import Any, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.media import MediaType
from app.schema.media import MediaItemBase
from app.schema.search import SearchResult
from app.services import media_service


class SearchSource(str, enum.Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"
    GOOGLE_BOOKS = "google_books"
    TMDB = "tmdb"
    IGDB = "igdb"
    LASTFM = "lastfm"


SEARCH_CONNECTOR_SOURCES = {
    SearchSource.GOOGLE_BOOKS,
    SearchSource.TMDB,
    SearchSource.IGDB,
    SearchSource.LASTFM,
}

DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 50
DEFAULT_EXTERNAL_PER_SOURCE = 1
MAX_EXTERNAL_PER_SOURCE = 5

router = APIRouter()


@router.get("", response_model=SearchResult)
async def search(
    q: str = Query(..., min_length=2),
    types: List[MediaType] | None = Query(default=None, alias="types"),
    include_external: bool = Query(default=False),
    sources: list[SearchSource] | None = Query(default=None, alias="sources"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=DEFAULT_PER_PAGE, ge=1, le=MAX_PER_PAGE),
    external_per_source: int = Query(default=DEFAULT_EXTERNAL_PER_SOURCE, ge=1, le=MAX_EXTERNAL_PER_SOURCE),
    session: AsyncSession = Depends(get_db),
) -> SearchResult:
    include_internal = True
    connector_sources: list[str] = []
    allowed_media_types: set[MediaType] | None = set(types) if types else None

    def _filter_connectors_by_type(candidates: list[str]) -> list[str]:
        if not allowed_media_types:
            return candidates
        connector_types: dict[str, set[MediaType]] = {
            SearchSource.GOOGLE_BOOKS.value: {MediaType.BOOK},
            SearchSource.TMDB.value: {MediaType.MOVIE, MediaType.TV},
            SearchSource.IGDB.value: {MediaType.GAME},
            SearchSource.LASTFM.value: {MediaType.MUSIC},
        }
        return [
            candidate
            for candidate in candidates
            if not allowed_media_types.isdisjoint(connector_types.get(candidate, set()))
        ]

    if sources:
        include_internal = SearchSource.INTERNAL in sources
        if SearchSource.EXTERNAL in sources:
            connector_sources = _filter_connectors_by_type(list(media_service.DEFAULT_EXTERNAL_SOURCES))
        else:
            connector_sources = _filter_connectors_by_type(
                [source.value for source in sources if source in SEARCH_CONNECTOR_SOURCES]
            )
        if not include_internal and not connector_sources:
            include_internal = True
    else:
        if include_external:
            connector_sources = _filter_connectors_by_type(list(media_service.DEFAULT_EXTERNAL_SOURCES))

    offset = (page - 1) * per_page
    internal_items: list[MediaItemBase] = []
    total_internal = 0
    if include_internal:
        internal_results, total_internal = await media_service.search_media(
            session, query=q, media_types=types, offset=offset, limit=per_page
        )
        internal_items = [MediaItemBase.model_validate(item) for item in internal_results]

    items_by_id: dict[str, MediaItemBase] = {str(item.id): item for item in internal_items}
    metadata: dict[str, Any] = {
        "paging": {
            "page": page,
            "per_page": per_page,
            "offset": offset,
            "total_internal": total_internal,
        },
        "counts": {"internal": len(internal_items)},
        "source_counts": {"internal": len(internal_items)},
    }
    external_counts: dict[str, int] = {}
    if connector_sources:
        external_items, external_counts = await media_service.search_external_sources(
            session,
            q,
            per_source=external_per_source,
            sources=connector_sources,
            allowed_media_types=allowed_media_types,
        )
        for item in external_items:
            items_by_id[str(item.id)] = MediaItemBase.model_validate(item)
        external_total = sum(external_counts.values())
        metadata["counts"]["external_ingested"] = external_total
        source_counts = metadata["source_counts"]
        source_counts["external"] = external_total
        for source_name, count in external_counts.items():
            source_counts[source_name] = count

    source_parts: list[str] = []
    if include_internal:
        source_parts.append("internal")
    if connector_sources:
        source_parts.append("external")
    source_label = "+".join(source_parts) if source_parts else "none"

    return SearchResult(results=list(items_by_id.values()), source=source_label, metadata=metadata)
