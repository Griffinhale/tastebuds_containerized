"""Media catalog services including ingestion, dedupe, and search.

Invariants:
- External search is circuit-breaker guarded and preview-only until ingestion.
- Connector payload storage is bounded to enforce retention limits.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from time import monotonic
from typing import Any, Iterable, TypeAlias

from fastapi import HTTPException
from sqlalchemy import and_, func, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.ingestion import get_connector
from app.ingestion.base import ConnectorResult
from app.ingestion.observability import CircuitOpenError, ingestion_monitor
from app.models.media import (
    BookItem,
    GameItem,
    MediaItem,
    MediaSource,
    MediaType,
    MovieItem,
    MusicItem,
)
from app.schema.search import SearchResultItem
from app.services import search_preview_service

DEFAULT_EXTERNAL_SOURCES = ("google_books", "tmdb", "igdb", "lastfm")
SEARCH_CONFIG = "english_unaccent"
MAX_INTERNAL_QUERY_LENGTH = 256
DedupeKey: TypeAlias = tuple[str, ...]

logger = logging.getLogger("app.services.media")


def normalize_title(value: str) -> str:
    """Normalize titles for dedupe comparisons."""
    return " ".join(value.casefold().split())


def _normalize_search_text(value: str) -> str:
    if not value:
        return ""
    folded = value.casefold()
    normalized = unicodedata.normalize("NFKD", folded)
    stripped = "".join(char for char in normalized if not unicodedata.combining(char))
    cleaned = re.sub(r"[^\w\s]", " ", stripped)
    return " ".join(cleaned.split())


def _join_search_values(*values: Any) -> str:
    parts: list[str] = []
    for value in values:
        if not value:
            continue
        if isinstance(value, (list, tuple, set)):
            parts.extend(str(item) for item in value if item)
        else:
            parts.append(str(value))
    return " ".join(parts)


def _bounded_payload(payload: dict[str, Any], max_bytes: int, *, kind: str) -> dict[str, Any]:
    """Truncate oversized payloads while preserving a diagnostic preview."""
    if not payload:
        return {}
    if max_bytes <= 0:
        return {"truncated": True, "reason": f"{kind}_storage_disabled"}
    try:
        encoded = json.dumps(payload, default=str).encode("utf-8")
        size_bytes = len(encoded)
    except Exception:
        return {"truncated": True, "reason": f"{kind}_serialization_error"}
    if size_bytes <= max_bytes:
        return payload
    preview = encoded[:max_bytes].decode("utf-8", errors="ignore")
    return {
        "truncated": True,
        "reason": f"{kind}_payload_too_large",
        "size_bytes": size_bytes,
        "max_bytes": max_bytes,
        "preview": preview,
    }


def build_dedupe_key(
    *,
    media_type: MediaType,
    title: str,
    canonical_url: str | None,
    release_date: date | None,
) -> DedupeKey:
    """Build a deterministic dedupe key using URL or title/date fallbacks."""
    if canonical_url:
        return ("url", canonical_url.rstrip("/").casefold())
    normalized = normalize_title(title)
    if release_date:
        return ("type-title-date", media_type.value, normalized, release_date.isoformat())
    return ("type-title", media_type.value, normalized)


def build_dedupe_key_from_item(media_item: MediaItem) -> DedupeKey:
    """Generate a dedupe key from a stored media item."""
    return build_dedupe_key(
        media_type=media_item.media_type,
        title=media_item.title,
        canonical_url=media_item.canonical_url,
        release_date=media_item.release_date,
    )


def build_dedupe_key_from_result(result: ConnectorResult) -> DedupeKey:
    """Generate a dedupe key from an external connector result."""
    return build_dedupe_key(
        media_type=result.media_type,
        title=result.title,
        canonical_url=result.canonical_url,
        release_date=result.release_date,
    )


@dataclass(slots=True)
class ExternalSourceTiming:
    """Timing metadata for external connector calls."""
    search_ms: float | None = None
    fetch_ms: float = 0.0


@dataclass(slots=True)
class ExternalSearchHit:
    """Resolved search hit annotated with its source name."""
    source: str
    item: SearchResultItem


@dataclass(slots=True)
class ExternalSearchOutcome:
    """Aggregated external search response with counts and timings."""
    hits: list[ExternalSearchHit] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    deduped_counts: dict[str, int] = field(default_factory=dict)
    dedupe_reasons: dict[str, dict[str, int]] = field(default_factory=dict)
    timings_ms: dict[str, ExternalSourceTiming] = field(default_factory=dict)


async def prune_external_previews(session: AsyncSession) -> int:
    """Cleanup helper suitable for cron/worker jobs."""
    return await search_preview_service.prune_expired_previews(session)


async def prune_media_source_payloads(
    session: AsyncSession, *, retention_days: int | None = None
) -> int:
    """Scrub stale connector payloads to keep data retention bounded."""

    ttl_days = retention_days if retention_days is not None else settings.ingestion_payload_retention_days
    if ttl_days <= 0:
        return 0

    cutoff = datetime.utcnow() - timedelta(days=ttl_days)
    scrubbed_payload = {
        "redacted": True,
        "reason": "retention_expired",
        "stripped_at": datetime.utcnow().isoformat() + "Z",
        "retention_days": ttl_days,
    }
    stmt = (
        update(MediaSource)
        .where(MediaSource.fetched_at <= cutoff)
        .values(raw_payload=scrubbed_payload)
        .execution_options(synchronize_session="fetch")
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount or 0


async def get_media_by_id(session: AsyncSession, media_id: uuid.UUID) -> MediaItem | None:
    """Fetch a media item by primary key."""
    result = await session.execute(select(MediaItem).where(MediaItem.id == media_id))
    return result.scalar_one_or_none()


async def get_media_with_sources(session: AsyncSession, media_id: uuid.UUID) -> MediaItem | None:
    """Fetch a media item and preload its sources."""
    result = await session.execute(
        select(MediaItem)
        .options(
            selectinload(MediaItem.sources),
            selectinload(MediaItem.book),
            selectinload(MediaItem.movie),
            selectinload(MediaItem.game),
            selectinload(MediaItem.music),
        )
        .where(MediaItem.id == media_id)
    )
    return result.scalar_one_or_none()


async def search_media(
    session: AsyncSession,
    *,
    query: str,
    media_types: Iterable[MediaType] | None = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[MediaItem], int]:
    """Search stored media items by natural-language query with pagination support.

    Implementation notes:
    - Uses Postgres full-text search over title/description plus creator fields.
    - Weighted vectors keep exact title hits above broader metadata matches.
    - Non-Postgres engines fall back to normalized substring matching.
    """

    search_start = monotonic()
    normalized_query = query.strip()
    if not normalized_query:
        return [], 0
    original_length = len(normalized_query)
    if original_length > MAX_INTERNAL_QUERY_LENGTH:
        normalized_query = normalized_query[:MAX_INTERNAL_QUERY_LENGTH]

    query_truncated = original_length > MAX_INTERNAL_QUERY_LENGTH
    media_type_list = list(media_types) if media_types else None
    dialect_name = session.bind.dialect.name if session.bind else None

    if dialect_name != "postgresql":
        stmt = (
            select(MediaItem, BookItem, MovieItem, GameItem, MusicItem)
            .outerjoin(BookItem, BookItem.media_item_id == MediaItem.id)
            .outerjoin(MovieItem, MovieItem.media_item_id == MediaItem.id)
            .outerjoin(GameItem, GameItem.media_item_id == MediaItem.id)
            .outerjoin(MusicItem, MusicItem.media_item_id == MediaItem.id)
        )
        if media_type_list:
            stmt = stmt.where(MediaItem.media_type.in_(media_type_list))
        result = await session.execute(stmt)
        rows = result.all()
        normalized_query = _normalize_search_text(normalized_query)
        if not normalized_query:
            return [], 0
        scored: list[tuple[int, str, str, MediaItem]] = []
        for media_item, book, movie, game, music in rows:
            title_text = _normalize_search_text(media_item.title or "")
            subtitle_text = _normalize_search_text(media_item.subtitle or "")
            description_text = _normalize_search_text(media_item.description or "")
            metadata_text = _normalize_search_text(
                _join_search_values(
                    book.authors if book else None,
                    book.publisher if book else None,
                    book.isbn_10 if book else None,
                    book.isbn_13 if book else None,
                    movie.directors if movie else None,
                    movie.producers if movie else None,
                    game.developers if game else None,
                    game.publishers if game else None,
                    game.genres if game else None,
                    game.platforms if game else None,
                    music.artist_name if music else None,
                    music.album_name if music else None,
                )
            )
            score = 0
            if normalized_query in title_text:
                score = max(score, 4)
            if normalized_query in subtitle_text:
                score = max(score, 3)
            if normalized_query in description_text:
                score = max(score, 2)
            if normalized_query in metadata_text:
                score = max(score, 1)
            if score:
                scored.append((score, media_item.title.casefold(), str(media_item.id), media_item))
        scored.sort(key=lambda item: (-item[0], item[1], item[2]))
        total = len(scored)
        items = [item[3] for item in scored][offset : offset + limit]
        search_ms = (monotonic() - search_start) * 1000
        logger.info(
            "Internal search completed",
            extra={
                "query_length": len(normalized_query),
                "query_truncated": query_truncated,
                "query_mode": "fallback",
                "offset": offset,
                "limit": limit,
                "returned": len(items),
                "total": total,
                "search_ms": round(search_ms, 2),
                "media_types": [media_type.value for media_type in media_type_list] if media_type_list else None,
            },
        )
        return items, total

    def _build_stmt(ts_query):
        rank = func.ts_rank_cd(MediaItem.search_vector, ts_query).label("rank")
        # Window count avoids a second round-trip; if deep pagination needs tuning, skip this when offset > 0.
        total_count = func.count().over().label("total_count")
        stmt = select(MediaItem, total_count, rank).where(MediaItem.search_vector.op("@@")(ts_query))
        if media_type_list:
            stmt = stmt.where(MediaItem.media_type.in_(media_type_list))
        return stmt.order_by(rank.desc(), func.lower(MediaItem.title), MediaItem.id).offset(offset).limit(limit)

    search_query = func.websearch_to_tsquery(SEARCH_CONFIG, normalized_query)
    query_mode = "websearch"
    try:
        result = await session.execute(_build_stmt(search_query))
    except DBAPIError:
        await session.rollback()
        search_query = func.plainto_tsquery(SEARCH_CONFIG, normalized_query)
        query_mode = "plain"
        result = await session.execute(_build_stmt(search_query))

    rows = result.all()
    items = [row[0] for row in rows]
    total = rows[0].total_count if rows else 0
    search_ms = (monotonic() - search_start) * 1000
    logger.info(
        "Internal search completed",
        extra={
            "query_length": len(normalized_query),
            "query_truncated": query_truncated,
            "query_mode": query_mode,
            "offset": offset,
            "limit": limit,
            "returned": len(items),
            "total": total,
            "search_ms": round(search_ms, 2),
            "media_types": [media_type.value for media_type in media_type_list] if media_type_list else None,
        },
    )
    return items, total


async def search_external_sources(
    session: AsyncSession,
    query: str,
    user_id: uuid.UUID,
    per_source: int = 1,
    sources: Iterable[str] | None = None,
    allowed_media_types: set[MediaType] | None = None,
    existing_keys: set[DedupeKey] | None = None,
) -> ExternalSearchOutcome:
    """Search external connectors and return deduped preview results.

    Implementation notes:
    - External calls are circuit-breaker gated per source.
    - Deduplication prefers canonical URLs, then title/date keys.
    """
    normalized_sources: list[str] = []
    seen: set[str] = set()
    source_candidates = sources or DEFAULT_EXTERNAL_SOURCES
    for source in source_candidates:
        normalized = source.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        if normalized in DEFAULT_EXTERNAL_SOURCES:
            normalized_sources.append(normalized)

    await search_preview_service.prune_expired_previews(session)

    dedupe_keys: set[DedupeKey] = set(existing_keys or [])
    aggregated: list[ExternalSearchHit] = []
    counts: dict[str, int] = {source: 0 for source in normalized_sources}
    deduped_counts: dict[str, int] = {source: 0 for source in normalized_sources}
    dedupe_reasons: dict[str, dict[str, int]] = {source: {} for source in normalized_sources}
    timings: dict[str, ExternalSourceTiming] = {
        source: ExternalSourceTiming() for source in normalized_sources
    }
    for source in normalized_sources:
        try:
            connector = get_connector(source)
        except ValueError:
            continue
        if not ingestion_monitor.allow_call(source):
            await ingestion_monitor.record_skip(source, "search", reason="circuit_open", context={"query": query})
            continue
        search_start = monotonic()
        try:
            identifiers = await ingestion_monitor.track(
                source,
                "search",
                lambda: connector.search(query, limit=per_source),
                context={"query": query},
            )
        except CircuitOpenError:
            continue
        except Exception:
            continue
        timings[source].search_ms = (monotonic() - search_start) * 1000
        seen_ids: set[str] = set()
        for identifier in identifiers[:per_source]:
            if not identifier or identifier in seen_ids:
                continue
            seen_ids.add(identifier)
            if not ingestion_monitor.allow_call(source):
                await ingestion_monitor.record_skip(
                    source,
                    "fetch",
                    reason="circuit_open",
                    context={"identifier": identifier},
                )
                continue
            try:
                fetch_start = monotonic()
                result = await ingestion_monitor.track(
                    source,
                    "fetch",
                    lambda ident=identifier: connector.fetch(ident),
                    context={"identifier": identifier},
                )
            except CircuitOpenError:
                continue
            except Exception:
                continue
            timings[source].fetch_ms += (monotonic() - fetch_start) * 1000
            if allowed_media_types and result.media_type not in allowed_media_types:
                continue
            dedupe_key = build_dedupe_key_from_result(result)
            if dedupe_key in dedupe_keys:
                deduped_counts[source] += 1
                reason_key = dedupe_key[0] if dedupe_key else "unknown"
                reason_label = {
                    "url": "canonical_url",
                    "type-title-date": "title_release_date",
                    "type-title": "title_only",
                }.get(reason_key, reason_key)
                dedupe_reasons[source][reason_label] = dedupe_reasons[source].get(reason_label, 0) + 1
                continue
            dedupe_keys.add(dedupe_key)
            preview = await search_preview_service.cache_connector_result(session, user_id, result)
            item_model = SearchResultItem.model_validate(
                {
                    "id": preview.id,
                    "media_type": result.media_type,
                    "title": result.title,
                    "description": result.description,
                    "release_date": result.release_date,
                    "cover_image_url": result.cover_image_url,
                    "canonical_url": result.canonical_url,
                    "metadata": result.metadata or None,
                    "source_name": result.source_name,
                    "source_id": result.source_id,
                    "preview_id": preview.id,
                    "preview_expires_at": preview.expires_at,
                }
            )
            aggregated.append(ExternalSearchHit(source=source, item=item_model))
            counts[source] += 1
    return ExternalSearchOutcome(
        hits=aggregated,
        counts=counts,
        deduped_counts=deduped_counts,
        dedupe_reasons=dedupe_reasons,
        timings_ms=timings,
    )


async def ingest_from_source(
    session: AsyncSession, *, source: str, identifier: str, force_refresh: bool = False
) -> MediaItem:
    """Fetch a single item from an external source and store it."""
    connector = get_connector(source)
    if not ingestion_monitor.allow_call(source):
        await ingestion_monitor.record_skip(
            source,
            "fetch",
            reason="circuit_open",
            context={"identifier": identifier, "force_refresh": force_refresh},
        )
        raise HTTPException(status_code=503, detail=f"{source} temporarily unavailable")
    try:
        result = await ingestion_monitor.track(
            source,
            "fetch",
            lambda: connector.fetch(identifier),
            context={"identifier": identifier, "force_refresh": force_refresh},
        )
    except CircuitOpenError as exc:
        raise HTTPException(status_code=503, detail=f"{source} temporarily unavailable") from exc
    return await upsert_media(session, result, force_refresh=force_refresh)


async def upsert_media(
    session: AsyncSession, connector_result: ConnectorResult, force_refresh: bool = False
) -> MediaItem:
    """Insert or update media items and sources from a connector result.

    Implementation notes:
    - Payloads are truncated to configured byte limits before storage.
    - Extensions are updated in place to preserve media item identity.
    """
    bounded_raw_payload = _bounded_payload(
        connector_result.raw_payload or {}, settings.ingestion_payload_max_bytes, kind="raw_ingestion"
    )
    bounded_metadata = _bounded_payload(
        connector_result.metadata or {}, settings.ingestion_metadata_max_bytes, kind="metadata"
    )
    connector_result.metadata = bounded_metadata
    connector_result.raw_payload = bounded_raw_payload

    existing = await session.execute(
        select(MediaSource).where(
            and_(
                MediaSource.source_name == connector_result.source_name,
                MediaSource.external_id == connector_result.source_id,
            )
        )
    )
    media_source = existing.scalar_one_or_none()

    if media_source and not force_refresh:
        media_item = await get_media_by_id(session, media_source.media_item_id)
        if media_item:
            return media_item

    extension_relationships = ["book", "movie", "game", "music"]

    if media_source:
        media_item = await get_media_by_id(session, media_source.media_item_id)
        if not media_item:
            raise HTTPException(status_code=404, detail="Media item missing")
        await session.refresh(media_item, attribute_names=extension_relationships)
        await _apply_result_to_item(media_item, connector_result)
        media_source.raw_payload = connector_result.raw_payload
        media_source.canonical_url = connector_result.source_url
        media_source.fetched_at = datetime.utcnow()
    else:
        media_item = MediaItem(
            media_type=connector_result.media_type,
            title=connector_result.title,
            subtitle=None,
            description=connector_result.description,
            release_date=connector_result.release_date,
            cover_image_url=connector_result.cover_image_url,
            canonical_url=connector_result.canonical_url,
            metadata=connector_result.metadata,
        )
        await _apply_result_to_item(media_item, connector_result)
        session.add(media_item)
        await session.flush()
        media_source = MediaSource(
            media_item_id=media_item.id,
            source_name=connector_result.source_name,
            external_id=connector_result.source_id,
            canonical_url=connector_result.source_url,
            raw_payload=connector_result.raw_payload,
            fetched_at=datetime.utcnow(),
        )
        session.add(media_source)

    await session.commit()
    await session.refresh(media_item, attribute_names=extension_relationships)
    return media_item


async def _apply_result_to_item(media_item: MediaItem, connector_result: ConnectorResult) -> None:
    """Apply connector fields and extensions onto a media item instance."""
    media_item.media_type = connector_result.media_type
    media_item.title = connector_result.title
    media_item.description = connector_result.description
    media_item.release_date = connector_result.release_date
    media_item.cover_image_url = connector_result.cover_image_url
    media_item.canonical_url = connector_result.canonical_url
    media_item.metadata = connector_result.metadata

    extensions = connector_result.extensions or {}
    if "book" in extensions:
        payload = extensions["book"]
        if media_item.book:
            media_item.book.authors = payload.get("authors")
            media_item.book.page_count = payload.get("page_count")
            media_item.book.publisher = payload.get("publisher")
            media_item.book.language = payload.get("language")
            media_item.book.isbn_10 = payload.get("isbn_10")
            media_item.book.isbn_13 = payload.get("isbn_13")
        else:
            media_item.book = BookItem(**payload)
    if "movie" in extensions:
        payload = extensions["movie"]
        if media_item.movie:
            media_item.movie.runtime_minutes = payload.get("runtime_minutes")
            media_item.movie.directors = payload.get("directors")
            media_item.movie.producers = payload.get("producers")
            media_item.movie.tmdb_type = payload.get("tmdb_type")
        else:
            media_item.movie = MovieItem(**payload)
    if "game" in extensions:
        payload = extensions["game"]
        if media_item.game:
            media_item.game.platforms = payload.get("platforms")
            media_item.game.developers = payload.get("developers")
            media_item.game.publishers = payload.get("publishers")
            media_item.game.genres = payload.get("genres")
        else:
            media_item.game = GameItem(**payload)
    if "music" in extensions:
        payload = extensions["music"]
        if media_item.music:
            media_item.music.artist_name = payload.get("artist_name")
            media_item.music.album_name = payload.get("album_name")
            media_item.music.track_number = payload.get("track_number")
            media_item.music.duration_ms = payload.get("duration_ms")
        else:
            media_item.music = MusicItem(**payload)


async def ensure_media_item(
    session: AsyncSession, *, title: str, media_type: MediaType, description: str | None = None
) -> MediaItem:
    """Return an existing item or create a new one for the given title/type."""
    existing = await session.execute(
        select(MediaItem).where(and_(MediaItem.title == title, MediaItem.media_type == media_type))
    )
    media_item = existing.scalar_one_or_none()
    if media_item:
        return media_item
    media_item = MediaItem(media_type=media_type, title=title, description=description)
    session.add(media_item)
    await session.commit()
    await session.refresh(media_item)
    return media_item
