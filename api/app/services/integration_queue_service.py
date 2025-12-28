"""Integration ingest queue helpers for webhook-driven workflows."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration import IntegrationIngestEvent, IntegrationIngestStatus
from app.services import media_service

logger = logging.getLogger("app.services.integration_queue")

SUPPORTED_INGEST_SOURCES = {"tmdb"}


def _utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    now = datetime.utcnow()
    return now if now.tzinfo else now.replace(tzinfo=timezone.utc)


def _arr_event_to_ingest(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract ingestion identifiers from Arr webhook payloads."""
    event_type = payload.get("eventType") or payload.get("event_type")
    movie = payload.get("movie") or payload.get("remoteMovie")
    series = payload.get("series")
    title = None
    tmdb_id = None
    media_kind = None
    if movie:
        title = movie.get("title") or payload.get("movieFile", {}).get("relativePath")
        tmdb_id = movie.get("tmdbId")
        media_kind = "movie"
    elif series:
        title = series.get("title")
        tmdb_id = series.get("tmdbId")
        media_kind = "tv"
    source_name = "tmdb" if tmdb_id else None
    source_id = f"{media_kind}:{tmdb_id}" if tmdb_id and media_kind else None
    return {
        "event_type": event_type,
        "title": title,
        "source_name": source_name,
        "source_id": source_id,
    }


async def record_arr_event(
    session: AsyncSession, *, user_id: uuid.UUID, provider: str, payload: dict[str, Any]
) -> IntegrationIngestEvent:
    """Persist an Arr webhook payload as a queue entry."""
    extracted = _arr_event_to_ingest(payload)
    status_value = IntegrationIngestStatus.PENDING if extracted["source_name"] else IntegrationIngestStatus.SKIPPED
    error = None if extracted["source_name"] else "missing_tmdb_id"
    event = IntegrationIngestEvent(
        user_id=user_id,
        provider=provider,
        event_type=extracted["event_type"],
        source_name=extracted["source_name"],
        source_id=extracted["source_id"],
        title=extracted["title"],
        status=status_value,
        payload=payload,
        error=error,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


async def list_ingest_events(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    provider: str,
    status_filter: str | None = None,
    limit: int = 50,
) -> list[IntegrationIngestEvent]:
    """List queued ingest events for a provider."""
    stmt = select(IntegrationIngestEvent).where(
        IntegrationIngestEvent.user_id == user_id,
        IntegrationIngestEvent.provider == provider,
    )
    if status_filter:
        stmt = stmt.where(IntegrationIngestEvent.status == IntegrationIngestStatus(status_filter))
    stmt = stmt.order_by(desc(IntegrationIngestEvent.created_at)).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()


async def ingest_event(
    session: AsyncSession, *, user_id: uuid.UUID, event_id: uuid.UUID
) -> IntegrationIngestEvent:
    """Ingest a queued event into the media catalog."""
    stmt = select(IntegrationIngestEvent).where(
        IntegrationIngestEvent.id == event_id,
        IntegrationIngestEvent.user_id == user_id,
    )
    event = await session.scalar(stmt)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingest event not found")
    if event.status != IntegrationIngestStatus.PENDING:
        return event
    if not event.source_name or not event.source_id:
        event.status = IntegrationIngestStatus.SKIPPED
        event.error = "missing_source_identifier"
        event.processed_at = _utcnow()
        await session.commit()
        return event
    if event.source_name not in SUPPORTED_INGEST_SOURCES:
        event.status = IntegrationIngestStatus.SKIPPED
        event.error = f"unsupported_source:{event.source_name}"
        event.processed_at = _utcnow()
        await session.commit()
        return event
    try:
        media_item = await media_service.ingest_from_source(
            session,
            source=event.source_name,
            identifier=event.source_id,
            force_refresh=False,
        )
    except Exception as exc:
        logger.warning("Ingest failed for event %s: %s", event.id, exc)
        event.status = IntegrationIngestStatus.FAILED
        event.error = str(exc)[:490]
        event.processed_at = _utcnow()
        await session.commit()
        return event
    event.status = IntegrationIngestStatus.INGESTED
    event.media_item_id = media_item.id
    event.processed_at = _utcnow()
    await session.commit()
    await session.refresh(event)
    return event


async def dismiss_event(
    session: AsyncSession, *, user_id: uuid.UUID, event_id: uuid.UUID
) -> IntegrationIngestEvent:
    """Mark a queued event as skipped."""
    stmt = select(IntegrationIngestEvent).where(
        IntegrationIngestEvent.id == event_id,
        IntegrationIngestEvent.user_id == user_id,
    )
    event = await session.scalar(stmt)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingest event not found")
    event.status = IntegrationIngestStatus.SKIPPED
    event.processed_at = _utcnow()
    await session.commit()
    await session.refresh(event)
    return event
