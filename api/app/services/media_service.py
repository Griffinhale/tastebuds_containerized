from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from time import monotonic
from typing import Iterable, TypeAlias

from fastapi import HTTPException
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
DedupeKey: TypeAlias = tuple[str, ...]


def normalize_title(value: str) -> str:
    return " ".join(value.casefold().split())


def build_dedupe_key(
    *,
    media_type: MediaType,
    title: str,
    canonical_url: str | None,
    release_date: date | None,
) -> DedupeKey:
    if canonical_url:
        return ("url", canonical_url.rstrip("/").casefold())
    normalized = normalize_title(title)
    if release_date:
        return ("type-title-date", media_type.value, normalized, release_date.isoformat())
    return ("type-title", media_type.value, normalized)


def build_dedupe_key_from_item(media_item: MediaItem) -> DedupeKey:
    return build_dedupe_key(
        media_type=media_item.media_type,
        title=media_item.title,
        canonical_url=media_item.canonical_url,
        release_date=media_item.release_date,
    )


def build_dedupe_key_from_result(result: ConnectorResult) -> DedupeKey:
    return build_dedupe_key(
        media_type=result.media_type,
        title=result.title,
        canonical_url=result.canonical_url,
        release_date=result.release_date,
    )


@dataclass(slots=True)
class ExternalSourceTiming:
    search_ms: float | None = None
    fetch_ms: float = 0.0


@dataclass(slots=True)
class ExternalSearchHit:
    source: str
    item: SearchResultItem


@dataclass(slots=True)
class ExternalSearchOutcome:
    hits: list[ExternalSearchHit] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    deduped_counts: dict[str, int] = field(default_factory=dict)
    timings_ms: dict[str, ExternalSourceTiming] = field(default_factory=dict)


async def prune_external_previews(session: AsyncSession) -> int:
    """Cleanup helper suitable for cron/worker jobs."""
    return await search_preview_service.prune_expired_previews(session)


async def prune_media_source_payloads(
    session: AsyncSession, *, retention_days: int | None = None
) -> int:
    """Scrub stale connector payloads to keep data retention bounded."""

    from app.core.config import settings

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
        .execution_options(synchronize_session=False)
    )
    result = await session.execute(stmt)
    await session.commit()
    session.sync_session.expire_all()
    return result.rowcount or 0


async def get_media_by_id(session: AsyncSession, media_id: uuid.UUID) -> MediaItem | None:
    result = await session.execute(select(MediaItem).where(MediaItem.id == media_id))
    return result.scalar_one_or_none()


async def get_media_with_sources(session: AsyncSession, media_id: uuid.UUID) -> MediaItem | None:
    result = await session.execute(
        select(MediaItem).options(selectinload(MediaItem.sources)).where(MediaItem.id == media_id)
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
    filtered_stmt = select(MediaItem).where(MediaItem.title.ilike(f"%{query}%"))
    if media_types:
        filtered_stmt = filtered_stmt.where(MediaItem.media_type.in_(list(media_types)))
    count_stmt = select(func.count()).select_from(filtered_stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()
    paged_stmt = filtered_stmt.order_by(func.lower(MediaItem.title)).offset(offset).limit(limit)
    result = await session.execute(paged_stmt)
    return result.scalars().all(), total


async def search_external_sources(
    session: AsyncSession,
    query: str,
    user_id: uuid.UUID,
    per_source: int = 1,
    sources: Iterable[str] | None = None,
    allowed_media_types: set[MediaType] | None = None,
    existing_keys: set[DedupeKey] | None = None,
) -> ExternalSearchOutcome:
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
        timings_ms=timings,
    )


async def ingest_from_source(
    session: AsyncSession, *, source: str, identifier: str, force_refresh: bool = False
) -> MediaItem:
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
        )
        session.add(media_source)

    await session.commit()
    await session.refresh(media_item, attribute_names=extension_relationships)
    return media_item


async def _apply_result_to_item(media_item: MediaItem, connector_result: ConnectorResult) -> None:
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
