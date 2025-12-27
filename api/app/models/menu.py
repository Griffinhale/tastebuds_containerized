"""Menu, course, and course item models for curated lists."""

from __future__ import annotations

import typing
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    owner: Mapped["User"] = relationship(back_populates="menus")
    courses: Mapped[list["Course"]] = relationship(
        back_populates="menu", cascade="all, delete-orphan", order_by="Course.position"
    )


class Course(Base):
    """Course grouping within a menu with explicit ordering."""
    __tablename__ = "courses"
    __table_args__ = (UniqueConstraint("menu_id", "position", name="uq_course_position"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    menu_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("menus.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    menu: Mapped[Menu] = relationship(back_populates="courses")
    items: Mapped[list["CourseItem"]] = relationship(
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

    course: Mapped[Course] = relationship(back_populates="items")
    media_item: Mapped["MediaItem"] = relationship(back_populates="course_items")
