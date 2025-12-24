from __future__ import annotations

import typing
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.media import JSON_COMPATIBLE, MediaType


class ExternalSearchPreview(Base):
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", backref="external_search_previews")


class UserExternalSearchQuota(Base):
    __tablename__ = "user_external_search_quotas"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    user = relationship("User", backref="external_search_quota")
