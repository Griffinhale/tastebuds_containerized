from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import date
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_optional_current_user
from app.models.media import MediaType
from app.models.user import User
from app.schema.search import SearchResult, SearchResultItem
from app.services import media_service, search_preview_service


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


@dataclass(slots=True)
class AggregatedSearchHit:
    item: SearchResultItem
    origin: str
    source: str
    source_rank: int


@router.get("", response_model=SearchResult)
async def search(
    q: str = Query(..., min_length=2),
    types: List[MediaType] | None = Query(default=None, alias="types"),
    include_external: bool = Query(default=False),
    sources: list[SearchSource] | None = Query(default=None, alias="sources"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=DEFAULT_PER_PAGE, ge=1, le=MAX_PER_PAGE),
    external_per_source: int = Query(default=DEFAULT_EXTERNAL_PER_SOURCE, ge=1, le=MAX_EXTERNAL_PER_SOURCE),
    current_user: User | None = Depends(get_optional_current_user),
    session: AsyncSession = Depends(get_db),
) -> SearchResult:
    include_internal = True
    connector_sources: list[str] = []
    allowed_media_types: set[MediaType] | None = set(types) if types else None

    external_requested = include_external
    if sources:
        external_requested = external_requested or any(
            source == SearchSource.EXTERNAL or source in SEARCH_CONNECTOR_SOURCES for source in sources
        )
    if external_requested and not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for external search",
        )

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
        include_internal = SearchSource.INTERNAL in sources or include_external
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
    internal_items: list[SearchResultItem] = []
    total_internal = 0
    dedupe_keys: set[media_service.DedupeKey] = set()
    merged_hits: list[AggregatedSearchHit] = []
    if include_internal:
        internal_results, total_internal = await media_service.search_media(
            session, query=q, media_types=types, offset=offset, limit=per_page
        )
        internal_items = [SearchResultItem.model_validate(item) for item in internal_results]
        dedupe_keys = {
            media_service.build_dedupe_key(
                media_type=item.media_type,
                title=item.title,
                canonical_url=item.canonical_url,
                release_date=item.release_date,
            )
            for item in internal_items
        }
        merged_hits.extend(
            AggregatedSearchHit(item=item, origin="internal", source="internal", source_rank=0)
            for item in internal_items
        )

    source_order = {name: index for index, name in enumerate(connector_sources)}
    external_source_counts: dict[str, int] = {}
    external_deduped_total = 0
    external_outcome: media_service.ExternalSearchOutcome | None = None
    if connector_sources and current_user:
        await search_preview_service.enforce_search_quota(session, current_user.id)
        external_outcome = await media_service.search_external_sources(
            session,
            q,
            current_user.id,
            per_source=external_per_source,
            sources=connector_sources,
            allowed_media_types=allowed_media_types,
            existing_keys=dedupe_keys,
        )
        for hit in external_outcome.hits:
            merged_hits.append(
                AggregatedSearchHit(
                    item=hit.item,
                    origin="external",
                    source=hit.source,
                    source_rank=source_order.get(hit.source, len(source_order)),
                )
            )
            external_source_counts[hit.source] = external_source_counts.get(hit.source, 0) + 1
        external_deduped_total = sum(external_outcome.deduped_counts.values())

    source_parts: list[str] = []
    if include_internal:
        source_parts.append("internal")
    if connector_sources:
        source_parts.append("external")
    source_label = "+".join(source_parts) if source_parts else "none"

    def _sort_key(hit: AggregatedSearchHit) -> tuple[Any, ...]:
        release_key: date | None = hit.item.release_date if isinstance(hit.item.release_date, date) else None
        return (
            0 if hit.origin == "internal" else 1,
            hit.source_rank,
            media_service.normalize_title(hit.item.title),
            release_key or date.max,
            str(hit.item.id),
        )

    ordered_hits = sorted(merged_hits, key=_sort_key)
    results = [hit.item for hit in ordered_hits]
    internal_count = len(internal_items)
    metadata: dict[str, Any] = {
        "paging": {
            "page": page,
            "per_page": per_page,
            "offset": offset,
            "total_internal": total_internal,
        },
        "counts": {"internal": internal_count},
        "source_counts": {"internal": internal_count},
        "source_metrics": {"internal": {"returned": internal_count}},
    }
    if connector_sources and external_outcome:
        ingested_total = sum(external_outcome.counts.values())
        returned_total = sum(external_source_counts.values())
        metadata["counts"]["external_ingested"] = ingested_total
        metadata["counts"]["external_returned"] = returned_total
        metadata["counts"]["external_deduped"] = external_deduped_total
        source_counts = metadata["source_counts"]
        source_counts["external"] = returned_total
        for source_name in connector_sources:
            source_counts[source_name] = external_source_counts.get(source_name, 0)
            timing = external_outcome.timings_ms.get(source_name)
            metadata["source_metrics"][source_name] = {
                "returned": external_source_counts.get(source_name, 0),
                "ingested": external_outcome.counts.get(source_name, 0),
                "deduped": external_outcome.deduped_counts.get(source_name, 0),
                "search_ms": timing.search_ms if timing else None,
                "fetch_ms": timing.fetch_ms if timing else 0.0,
            }

    return SearchResult(results=results, source=source_label, metadata=metadata)
