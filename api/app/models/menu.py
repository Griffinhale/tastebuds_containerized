"""Menu, course, and course item models for curated lists."""

from __future__ import annotations

import typing
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship as sa_relationship

from app.db.base_class import Base

if typing.TYPE_CHECKING:  # pragma: no cover
    from app.models.media import MediaItem
    from app.models.user import User


class Menu(Base):
    """Menu header metadata and owner relationship."""
    __tablename__ = "menus"
    __table_args__ = (UniqueConstraint("slug", name="uq_menu_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    owner: Mapped["User"] = sa_relationship(back_populates="menus")
    courses: Mapped[list["Course"]] = sa_relationship(
        back_populates="menu", cascade="all, delete-orphan", order_by="Course.position"
    )
    forks: Mapped[list["MenuLineage"]] = sa_relationship(
        back_populates="source_menu",
        cascade="all, delete-orphan",
        foreign_keys="MenuLineage.source_menu_id",
    )
    forked_from: Mapped["MenuLineage | None"] = sa_relationship(
        back_populates="forked_menu",
        foreign_keys="MenuLineage.forked_menu_id",
        uselist=False,
    )
    pairings: Mapped[list["MenuItemPairing"]] = sa_relationship(
        back_populates="menu",
        cascade="all, delete-orphan",
        order_by="MenuItemPairing.created_at",
    )
    share_tokens: Mapped[list["MenuShareToken"]] = sa_relationship(
        back_populates="menu",
        cascade="all, delete-orphan",
        order_by="MenuShareToken.created_at",
    )


class Course(Base):
    """Course grouping within a menu with explicit ordering and narrative intent."""
    __tablename__ = "courses"
    __table_args__ = (UniqueConstraint("menu_id", "position", name="uq_course_position"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    menu_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("menus.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    intent: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    menu: Mapped[Menu] = sa_relationship(back_populates="courses")
    items: Mapped[list["CourseItem"]] = sa_relationship(
        back_populates="course", cascade="all, delete-orphan", order_by="CourseItem.position"
    )


class CourseItem(Base):
    """Item placement within a course with stable ordering."""
    __tablename__ = "course_items"
    __table_args__ = (UniqueConstraint("course_id", "position", name="uq_course_items_position"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"))
    media_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_items.id", ondelete="CASCADE"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    course: Mapped[Course] = sa_relationship(back_populates="items")
    media_item: Mapped["MediaItem"] = sa_relationship(back_populates="course_items")
    pairings_as_primary: Mapped[list["MenuItemPairing"]] = sa_relationship(
        back_populates="primary_item",
        foreign_keys="MenuItemPairing.primary_course_item_id",
        cascade="all, delete-orphan",
    )
    pairings_as_secondary: Mapped[list["MenuItemPairing"]] = sa_relationship(
        back_populates="paired_item",
        foreign_keys="MenuItemPairing.paired_course_item_id",
        cascade="all, delete-orphan",
    )


class MenuLineage(Base):
    """Attribution link between a menu and its forked copy."""
    __tablename__ = "menu_lineage"
    __table_args__ = (UniqueConstraint("source_menu_id", "forked_menu_id", name="uq_menu_lineage"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_menu_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("menus.id", ondelete="CASCADE"), nullable=False
    )
    forked_menu_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("menus.id", ondelete="CASCADE"), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    source_menu: Mapped["Menu"] = sa_relationship(
        back_populates="forks", foreign_keys=[source_menu_id]
    )
    forked_menu: Mapped["Menu"] = sa_relationship(
        back_populates="forked_from", foreign_keys=[forked_menu_id]
    )
    creator: Mapped["User | None"] = sa_relationship(foreign_keys=[created_by])


class MenuItemPairing(Base):
    """Cross-media pairing between two course items."""
    __tablename__ = "menu_item_pairings"
    __table_args__ = (
        UniqueConstraint(
            "menu_id",
            "primary_course_item_id",
            "paired_course_item_id",
            name="uq_menu_pairing",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    menu_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("menus.id", ondelete="CASCADE"), nullable=False
    )
    primary_course_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("course_items.id", ondelete="CASCADE"), nullable=False
    )
    paired_course_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("course_items.id", ondelete="CASCADE"), nullable=False
    )
    relationship: Mapped[str | None] = mapped_column(String(120))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    menu: Mapped["Menu"] = sa_relationship(back_populates="pairings")
    primary_item: Mapped["CourseItem"] = sa_relationship(
        back_populates="pairings_as_primary", foreign_keys=[primary_course_item_id]
    )
    paired_item: Mapped["CourseItem"] = sa_relationship(
        back_populates="pairings_as_secondary", foreign_keys=[paired_course_item_id]
    )


class MenuShareToken(Base):
    """Ephemeral share tokens for draft menus."""
    __tablename__ = "menu_share_tokens"
    __table_args__ = (UniqueConstraint("token", name="uq_menu_share_token"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    menu_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("menus.id", ondelete="CASCADE"), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    menu: Mapped["Menu"] = sa_relationship(back_populates="share_tokens")
    creator: Mapped["User | None"] = sa_relationship(foreign_keys=[created_by])
