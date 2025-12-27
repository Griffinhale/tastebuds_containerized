"""Media catalog models, including typed extensions and sources."""

from __future__ import annotations

import enum
import typing
import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

JSON_COMPATIBLE = JSON().with_variant(JSONB, "postgresql")

if typing.TYPE_CHECKING:  # pragma: no cover
    from app.models.menu import CourseItem
    from app.models.tagging import MediaItemTag
    from app.models.user import User


class MediaType(str, enum.Enum):
    """Supported media categories for catalog items."""
    BOOK = "book"
    MOVIE = "movie"
    TV = "tv"
    GAME = "game"
    MUSIC = "music"


class UserItemStatus(str, enum.Enum):
    """Tracking statuses for a user's progress on a media item."""
    CONSUMED = "consumed"
    CONSUMING = "currently_consuming"
    WANT = "want_to_consume"
    PAUSED = "paused"
    DROPPED = "dropped"


class UserItemLogType(str, enum.Enum):
    """Event types for logging user progress and goals."""
    STARTED = "started"
    PROGRESS = "progress"
    FINISHED = "finished"
    NOTE = "note"
    GOAL = "goal"


class MediaItem(Base):
    """Canonical media record shared across sources and menus."""
    __tablename__ = "media_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Persist the enum values (lowercase) instead of names (uppercase) so they match the DB enum
    media_type: Mapped[MediaType] = mapped_column(
        Enum(MediaType, name="media_type", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    subtitle: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None]
    release_date: Mapped[date | None] = mapped_column(Date)
    cover_image_url: Mapped[str | None] = mapped_column(String(1024))
    canonical_url: Mapped[str | None] = mapped_column(String(1024))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON_COMPATIBLE, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    book: Mapped["BookItem | None"] = relationship(back_populates="media_item", uselist=False)
    movie: Mapped["MovieItem | None"] = relationship(back_populates="media_item", uselist=False)
    game: Mapped["GameItem | None"] = relationship(back_populates="media_item", uselist=False)
    music: Mapped["MusicItem | None"] = relationship(back_populates="media_item", uselist=False)
    sources: Mapped[list["MediaSource"]] = relationship(back_populates="media_item", cascade="all, delete-orphan")
    tag_links: Mapped[list["MediaItemTag"]] = relationship(back_populates="media_item", cascade="all, delete-orphan")
    course_items: Mapped[list["CourseItem"]] = relationship(back_populates="media_item")
    user_states: Mapped[list["UserItemState"]] = relationship(back_populates="media_item", cascade="all, delete-orphan")
    user_logs: Mapped[list["UserItemLog"]] = relationship(back_populates="media_item", cascade="all, delete-orphan")


class BookItem(Base):
    """Book-specific extension fields for a media item."""
    __tablename__ = "book_items"

    media_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_items.id", ondelete="CASCADE"), primary_key=True
    )
    authors: Mapped[list[str] | None] = mapped_column(JSON_COMPATIBLE)
    page_count: Mapped[int | None]
    publisher: Mapped[str | None]
    language: Mapped[str | None]
    isbn_10: Mapped[str | None] = mapped_column(String(32))
    isbn_13: Mapped[str | None] = mapped_column(String(32))

    media_item: Mapped[MediaItem] = relationship(back_populates="book")


class MovieItem(Base):
    """Movie-specific extension fields for a media item."""
    __tablename__ = "movie_items"

    media_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_items.id", ondelete="CASCADE"), primary_key=True
    )
    runtime_minutes: Mapped[int | None]
    directors: Mapped[list[str] | None] = mapped_column(JSON_COMPATIBLE)
    producers: Mapped[list[str] | None] = mapped_column(JSON_COMPATIBLE)
    tmdb_type: Mapped[str | None]

    media_item: Mapped[MediaItem] = relationship(back_populates="movie")


class GameItem(Base):
    """Game-specific extension fields for a media item."""
    __tablename__ = "game_items"

    media_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_items.id", ondelete="CASCADE"), primary_key=True
    )
    platforms: Mapped[list[str] | None] = mapped_column(JSON_COMPATIBLE)
    developers: Mapped[list[str] | None] = mapped_column(JSON_COMPATIBLE)
    publishers: Mapped[list[str] | None] = mapped_column(JSON_COMPATIBLE)
    genres: Mapped[list[str] | None] = mapped_column(JSON_COMPATIBLE)

    media_item: Mapped[MediaItem] = relationship(back_populates="game")


class MusicItem(Base):
    """Music-specific extension fields for a media item."""
    __tablename__ = "music_items"

    media_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_items.id", ondelete="CASCADE"), primary_key=True
    )
    artist_name: Mapped[str | None]
    album_name: Mapped[str | None]
    track_number: Mapped[int | None]
    duration_ms: Mapped[int | None]

    media_item: Mapped[MediaItem] = relationship(back_populates="music")


class MediaSource(Base):
    """Upstream source payload metadata for a media item."""
    __tablename__ = "media_sources"
    __table_args__ = (UniqueConstraint("source_name", "external_id", name="uq_source_external"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(String(1024))
    raw_payload: Mapped[dict] = mapped_column(JSON_COMPATIBLE, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    media_item: Mapped[MediaItem] = relationship(back_populates="sources")


class UserItemState(Base):
    """Per-user state tracking for a media item."""
    __tablename__ = "user_item_states"
    __table_args__ = (
        UniqueConstraint("user_id", "media_item_id", name="uq_user_item"),
        CheckConstraint("rating >= 0 AND rating <= 10", name="ck_rating_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    media_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_items.id", ondelete="CASCADE")
    )
    status: Mapped[UserItemStatus] = mapped_column(
        Enum(UserItemStatus, name="user_item_status", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )
    rating: Mapped[int | None]
    favorite: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[str | None]
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship(back_populates="item_states")
    media_item: Mapped[MediaItem] = relationship(back_populates="user_states")


class UserItemLog(Base):
    """Per-user event log entries for media progress and goals."""
    __tablename__ = "user_item_logs"
    __table_args__ = (
        CheckConstraint("minutes_spent >= 0", name="ck_log_minutes_spent_nonnegative"),
        CheckConstraint("progress_percent >= 0 AND progress_percent <= 100", name="ck_log_progress_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    media_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_items.id", ondelete="CASCADE")
    )
    log_type: Mapped[UserItemLogType] = mapped_column(
        Enum(UserItemLogType, name="user_item_log_type", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(String(2000))
    minutes_spent: Mapped[int | None] = mapped_column(Integer)
    progress_percent: Mapped[int | None] = mapped_column(Integer)
    goal_target: Mapped[str | None] = mapped_column(String(255))
    goal_due_on: Mapped[date | None] = mapped_column(Date)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship(back_populates="item_logs")
    media_item: Mapped[MediaItem] = relationship(back_populates="user_logs")


def _get_metadata(media: MediaItem) -> dict | None:
    """Expose the JSON metadata field via a property alias."""
    return media.metadata_


def _set_metadata(media: MediaItem, value: dict | None) -> None:
    """Set metadata through the property alias."""
    media.metadata_ = value


MediaItem.metadata = property(_get_metadata, _set_metadata)
