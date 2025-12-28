"""Automation rule models for scheduled and event-driven workflows."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

JSON_COMPATIBLE = JSON().with_variant(JSONB, "postgresql")


class AutomationRule(Base):
    """User-defined automation rule with trigger/action metadata."""

    __tablename__ = "automation_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger_config: Mapped[dict | None] = mapped_column(JSON_COMPATIBLE)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    action_config: Mapped[dict | None] = mapped_column(JSON_COMPATIBLE)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User", backref="automation_rules")
