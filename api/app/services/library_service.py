"""Library aggregation helpers for state + log views."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.media import MediaItem, UserItemLog, UserItemState, UserItemStatus
from app.schema.library import LibraryItemRead, LibraryOverview, LibrarySummary


async def get_library_overview(session: AsyncSession, user_id: uuid.UUID) -> LibraryOverview:
    """Return a library snapshot with summary counts and next-up queue."""
    state_result = await session.execute(
        select(UserItemState)
        .options(selectinload(UserItemState.media_item))
        .where(UserItemState.user_id == user_id)
    )
    states = state_result.scalars().all()

    log_result = await session.execute(
        select(UserItemLog)
        .options(selectinload(UserItemLog.media_item))
        .where(UserItemLog.user_id == user_id)
        .order_by(UserItemLog.logged_at.desc(), UserItemLog.created_at.desc())
    )
    logs = log_result.scalars().all()

    entries: dict[uuid.UUID, dict[str, object]] = {}

    summary = _summarize_states(states)

    for state in states:
        entry = _ensure_entry(entries, state.media_item)
        entry["state"] = state
        entry["last_activity_at"] = _max_timestamp(entry.get("last_activity_at"), state.updated_at)

    log_counts: dict[uuid.UUID, int] = defaultdict(int)
    for log in logs:
        log_counts[log.media_item_id] += 1
        entry = entries.get(log.media_item_id)
        if entry is None:
            entry = _ensure_entry(entries, log.media_item)
        if entry.get("last_log") is None:
            entry["last_log"] = log
        entry["last_activity_at"] = _max_timestamp(entry.get("last_activity_at"), log.logged_at)

    for media_id, count in log_counts.items():
        entries[media_id]["log_count"] = count

    items = _sorted_entries(entries)
    next_up = _next_up_queue(items)

    summary.total = len(items)

    return LibraryOverview(summary=summary, items=items, next_up=next_up)


def _ensure_entry(entries: dict[uuid.UUID, dict[str, object]], media_item: MediaItem | None) -> dict[str, object]:
    """Create a base entry for a media item if missing."""
    if media_item is None:
        return {}
    entry = entries.setdefault(
        media_item.id,
        {
            "media_item": media_item,
            "state": None,
            "last_log": None,
            "log_count": 0,
            "last_activity_at": None,
        },
    )
    return entry


def _summarize_states(states: list[UserItemState]) -> LibrarySummary:
    """Build a status summary from user states."""
    summary = LibrarySummary()
    for state in states:
        if state.status == UserItemStatus.CONSUMED:
            summary.consumed += 1
        elif state.status == UserItemStatus.CONSUMING:
            summary.currently_consuming += 1
        elif state.status == UserItemStatus.WANT:
            summary.want_to_consume += 1
        elif state.status == UserItemStatus.PAUSED:
            summary.paused += 1
        elif state.status == UserItemStatus.DROPPED:
            summary.dropped += 1
    return summary


def _max_timestamp(current: datetime | None, candidate: datetime | None) -> datetime | None:
    """Return the most recent timestamp from the two inputs."""
    if current and candidate:
        try:
            return max(current, candidate)
        except TypeError:
            return current if _timestamp_value(current) >= _timestamp_value(candidate) else candidate
    return current or candidate


def _sorted_entries(entries: dict[uuid.UUID, dict[str, object]]) -> list[LibraryItemRead]:
    """Sort library entries by last activity and title."""
    def sort_key(entry: LibraryItemRead) -> tuple[bool, float]:
        last_activity = entry.last_activity_at
        return (last_activity is not None, _timestamp_value(last_activity) if last_activity else 0.0)

    items = [LibraryItemRead(**entry) for entry in entries.values() if entry]
    return sorted(items, key=sort_key, reverse=True)


def _next_up_queue(items: list[LibraryItemRead]) -> list[LibraryItemRead]:
    """Filter library entries into the next-up queue."""
    candidates: list[LibraryItemRead] = []
    for entry in items:
        state = entry.state
        if not state:
            continue
        if state.status in {UserItemStatus.WANT, UserItemStatus.CONSUMING, UserItemStatus.PAUSED}:
            candidates.append(entry)
    return candidates[:6]


def _timestamp_value(value: datetime) -> float:
    """Normalize timestamps for safe ordering comparisons."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc).timestamp()
    return value.timestamp()
