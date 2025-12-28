"""Availability CRUD and summary helpers."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Iterable

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media import AvailabilityStatus, MediaItemAvailability
from app.schema.media import AvailabilitySummary, MediaAvailabilityUpsert


async def list_availability(
    session: AsyncSession, media_item_id: uuid.UUID
) -> list[MediaItemAvailability]:
    """Return availability entries for a media item."""
    result = await session.execute(
        select(MediaItemAvailability)
        .where(MediaItemAvailability.media_item_id == media_item_id)
        .order_by(MediaItemAvailability.provider, MediaItemAvailability.region, MediaItemAvailability.format)
    )
    return result.scalars().all()


async def upsert_availability(
    session: AsyncSession,
    media_item_id: uuid.UUID,
    entries: Iterable[MediaAvailabilityUpsert],
) -> list[MediaItemAvailability]:
    """Upsert availability entries keyed by provider/region/format."""
    now = datetime.utcnow()
    result = await session.execute(
        select(MediaItemAvailability).where(MediaItemAvailability.media_item_id == media_item_id)
    )
    existing = {
        (item.provider, item.region, item.format): item for item in result.scalars().all()
    }

    for entry in entries:
        key = (entry.provider, entry.region, entry.format)
        last_checked = entry.last_checked_at or now
        if key in existing:
            record = existing[key]
            record.status = entry.status
            record.deeplink_url = entry.deeplink_url
            record.last_checked_at = last_checked
            record.updated_at = now
        else:
            session.add(
                MediaItemAvailability(
                    media_item_id=media_item_id,
                    provider=entry.provider,
                    region=entry.region,
                    format=entry.format,
                    status=entry.status,
                    deeplink_url=entry.deeplink_url,
                    last_checked_at=last_checked,
                )
            )

    await session.commit()
    return await list_availability(session, media_item_id)


async def get_availability_summary(
    session: AsyncSession, media_item_ids: Iterable[uuid.UUID]
) -> dict[uuid.UUID, AvailabilitySummary]:
    """Aggregate availability summaries keyed by media item ID."""
    ids = list({media_item_id for media_item_id in media_item_ids})
    if not ids:
        return {}
    result = await session.execute(
        select(MediaItemAvailability).where(MediaItemAvailability.media_item_id.in_(ids))
    )
    summaries: dict[uuid.UUID, AvailabilitySummary] = {}
    for entry in result.scalars():
        summary = summaries.get(entry.media_item_id)
        if not summary:
            summary = AvailabilitySummary()
            summaries[entry.media_item_id] = summary

        if entry.provider not in summary.providers:
            summary.providers.append(entry.provider)
        if entry.region not in summary.regions:
            summary.regions.append(entry.region)
        if entry.format not in summary.formats:
            summary.formats.append(entry.format)

        status_key = entry.status.value if isinstance(entry.status, AvailabilityStatus) else str(entry.status)
        summary.status_counts[status_key] = summary.status_counts.get(status_key, 0) + 1

        if entry.last_checked_at:
            if summary.last_checked_at is None or entry.last_checked_at > summary.last_checked_at:
                summary.last_checked_at = entry.last_checked_at

    return summaries


async def refresh_stale_availability(session: AsyncSession, *, stale_days: int = 7) -> int:
    """Mark stale availability entries as unknown.

    This is a placeholder refresh job until provider connectors populate live data.
    """
    if stale_days <= 0:
        return 0
    now = datetime.utcnow()
    cutoff = now - timedelta(days=stale_days)
    stmt = (
        update(MediaItemAvailability)
        .where(or_(MediaItemAvailability.last_checked_at.is_(None), MediaItemAvailability.last_checked_at <= cutoff))
        .values(status=AvailabilityStatus.UNKNOWN, last_checked_at=now, updated_at=now)
        .execution_options(synchronize_session="fetch")
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount or 0
