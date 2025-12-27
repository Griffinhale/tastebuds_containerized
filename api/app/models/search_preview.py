"""External search preview and quota tracking models."""

from __future__ import annotations

import typing
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.media import JSON_COMPATIBLE, MediaType


class ExternalSearchPreview(Base):
    """Short-lived preview record for external search results."""
    __tablename__ = "external_search_previews"
    __table_args__ = (
        UniqueConstraint("user_id", "source_name", "external_id", name="uq_preview_per_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_name: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[MediaType] = mapped_column(
        Enum(MediaType, name="media_type", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    cover_image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    metadata_payload: Mapped[dict | None] = mapped_column("metadata", JSON_COMPATIBLE, default=dict)
    raw_payload: Mapped[dict[str, typing.Any]] = mapped_column(JSON_COMPATIBLE, default=dict)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="external_search_previews")


class UserExternalSearchQuota(Base):
    """Per-user quota window tracking for external search fan-out."""
    __tablename__ = "user_external_search_quotas"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    user = relationship("User", backref="external_search_quota")


def _ensure_tz_aware(dt: datetime | None) -> datetime | None:
    """Normalize DB-loaded timestamps to UTC to avoid naive/aware comparisons in SQLite tests."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@event.listens_for(ExternalSearchPreview, "load")
@event.listens_for(ExternalSearchPreview, "refresh")
def _normalize_preview_timestamps(target: ExternalSearchPreview, *_, **__) -> None:
    """Normalize preview timestamps after load/refresh events."""
    target.expires_at = _ensure_tz_aware(target.expires_at)  # type: ignore[assignment]
    target.created_at = _ensure_tz_aware(target.created_at)  # type: ignore[assignment]


@event.listens_for(UserExternalSearchQuota, "load")
@event.listens_for(UserExternalSearchQuota, "refresh")
def _normalize_quota_timestamps(target: UserExternalSearchQuota, *_, **__) -> None:
    """Normalize quota window timestamps after load/refresh events."""
    target.window_start = _ensure_tz_aware(target.window_start)  # type: ignore[assignment]


@event.listens_for(ExternalSearchPreview.expires_at, "set", retval=True)
@event.listens_for(ExternalSearchPreview.created_at, "set", retval=True)
def _coerce_preview_dt(
    _target: ExternalSearchPreview, value: datetime | None, *_: object, **__: object
) -> datetime | None:
    """Coerce preview timestamps to UTC on assignment."""
    return _ensure_tz_aware(value)


@event.listens_for(UserExternalSearchQuota.window_start, "set", retval=True)
def _coerce_quota_dt(
    _target: UserExternalSearchQuota, value: datetime | None, *_: object, **__: object
) -> datetime | None:
    """Coerce quota window timestamps to UTC on assignment."""
    return _ensure_tz_aware(value)
