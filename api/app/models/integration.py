"""Integration models for webhook tokens and ingest queues."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

JSON_COMPATIBLE = JSON().with_variant(JSONB, "postgresql")


class IntegrationIngestStatus(str, enum.Enum):
    """Lifecycle states for inbound integration events."""
    PENDING = "pending"
    INGESTED = "ingested"
    SKIPPED = "skipped"
    FAILED = "failed"


class IntegrationWebhookToken(Base):
    """Hashed webhook token used to associate integration events to a user."""

    __tablename__ = "integration_webhook_tokens"
    __table_args__ = (UniqueConstraint("token_hash", name="uq_integration_webhook_token_hash"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    token_prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user = relationship("User", backref="integration_webhook_tokens")


class IntegrationIngestEvent(Base):
    """Inbound webhook payloads waiting to be ingested or mapped."""

    __tablename__ = "integration_ingest_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str | None] = mapped_column(String(120))
    source_name: Mapped[str | None] = mapped_column(String(64))
    source_id: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[IntegrationIngestStatus] = mapped_column(
        Enum(
            IntegrationIngestStatus,
            name="integration_ingest_status",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        default=IntegrationIngestStatus.PENDING,
        nullable=False,
    )
    payload: Mapped[dict | None] = mapped_column(JSON_COMPATIBLE)
    error: Mapped[str | None] = mapped_column(String(500))
    media_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user = relationship("User", backref="integration_ingest_events")
