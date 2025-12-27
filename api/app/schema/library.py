"""Library aggregation schemas for user media tracking."""

from __future__ import annotations

from datetime import datetime

from app.schema.base import ORMModel
from app.schema.media import MediaItemBase, UserItemLogRead, UserItemStateRead


class LibraryItemRead(ORMModel):
    """Combined library entry with state and log context."""
    media_item: MediaItemBase
    state: UserItemStateRead | None = None
    last_log: UserItemLogRead | None = None
    log_count: int = 0
    last_activity_at: datetime | None = None


class LibrarySummary(ORMModel):
    """Counts by status for quick status tracking."""
    total: int = 0
    consumed: int = 0
    currently_consuming: int = 0
    want_to_consume: int = 0
    paused: int = 0
    dropped: int = 0


class LibraryOverview(ORMModel):
    """Library snapshot with summary, next-up queue, and full list."""
    summary: LibrarySummary
    items: list[LibraryItemRead]
    next_up: list[LibraryItemRead]
