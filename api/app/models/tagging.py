from __future__ import annotations

import uuid

import typing

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if typing.TYPE_CHECKING:  # pragma: no cover
    from app.models.media import MediaItem


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("owner_id", "name", name="uq_owner_tag"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(64), nullable=False)

    media_links: Mapped[list["MediaItemTag"]] = relationship(
        back_populates="tag", cascade="all, delete-orphan"
    )


class MediaItemTag(Base):
    __tablename__ = "media_item_tags"
    __table_args__ = (
        UniqueConstraint("media_item_id", "tag_id", name="uq_media_tag"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_items.id", ondelete="CASCADE"), nullable=False
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), nullable=False
    )

    tag: Mapped[Tag] = relationship(back_populates="media_links")
    media_item: Mapped["MediaItem"] = relationship(back_populates="tag_links")
