"""User model with authentication and ownership relationships."""

from __future__ import annotations

import typing
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

JSON_COMPATIBLE = JSON().with_variant(JSONB, "postgresql")

if typing.TYPE_CHECKING:  # pragma: no cover
    from app.models.auth import RefreshToken
    from app.models.media import UserItemLog, UserItemState
    from app.models.menu import Menu


class User(Base):
    """Primary user account record."""
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    menus: Mapped[list["Menu"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    item_states: Mapped[list["UserItemState"]] = relationship(back_populates="user")
    item_logs: Mapped[list["UserItemLog"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    taste_profile: Mapped["UserTasteProfile | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )


class UserTasteProfile(Base):
    """Materialized summary of a user's taste signals."""
    __tablename__ = "user_taste_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_taste_profile"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    profile: Mapped[dict] = mapped_column(JSON_COMPATIBLE, default=dict)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship(back_populates="taste_profile")
