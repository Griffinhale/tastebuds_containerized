from __future__ import annotations

import uuid
from typing import Iterable, Sequence

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion import get_connector
from app.ingestion.base import ConnectorResult
from app.models.media import (
    BookItem,
    GameItem,
    MediaItem,
    MediaSource,
    MediaType,
    MovieItem,
    MusicItem,
)


async def get_media_by_id(session: AsyncSession, media_id: uuid.UUID) -> MediaItem | None:
    result = await session.execute(select(MediaItem).where(MediaItem.id == media_id))
    return result.scalar_one_or_none()


async def get_media_with_sources(session: AsyncSession, media_id: uuid.UUID) -> MediaItem | None:
    result = await session.execute(
        select(MediaItem)
        .options(selectinload(MediaItem.sources))
        .where(MediaItem.id == media_id)
    )
    return result.scalar_one_or_none()


async def search_media(
    session: AsyncSession, *, query: str, media_types: Iterable[MediaType] | None = None, limit: int = 20
) -> Sequence[MediaItem]:
    stmt = select(MediaItem).where(MediaItem.title.ilike(f"%{query}%"))
    if media_types:
        stmt = stmt.where(MediaItem.media_type.in_(list(media_types)))
    stmt = stmt.order_by(func.lower(MediaItem.title)).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()


async def search_external_sources(session: AsyncSession, query: str, per_source: int = 1) -> list[MediaItem]:
    aggregated: list[MediaItem] = []
    for source in ("google_books", "tmdb", "igdb", "lastfm"):
        try:
            connector = get_connector(source)
            identifiers = await connector.search(query, limit=per_source)
            for identifier in identifiers:
                result = await connector.fetch(identifier)
                media = await upsert_media(session, result)
                aggregated.append(media)
        except Exception:
            continue
    return aggregated


async def ingest_from_source(
    session: AsyncSession, *, source: str, identifier: str, force_refresh: bool = False
) -> MediaItem:
    connector = get_connector(source)
    result = await connector.fetch(identifier)
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
