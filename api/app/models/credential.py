from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class UserCredential(Base):
    __tablename__ = "user_credentials"
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_user_provider"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    encrypted_secret: Mapped[str] = mapped_column(String(4096), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)

    user = relationship("User", backref="credentials")


def _normalize_credential(target: UserCredential, *_, **__) -> None:
    if target.expires_at and target.expires_at.tzinfo is None:
        target.expires_at = target.expires_at.replace(tzinfo=timezone.utc)  # type: ignore[assignment]
    if target.rotated_at and target.rotated_at.tzinfo is None:
        target.rotated_at = target.rotated_at.replace(tzinfo=timezone.utc)  # type: ignore[assignment]
    if target.created_at.tzinfo is None:
        target.created_at = target.created_at.replace(tzinfo=timezone.utc)  # type: ignore[assignment]
    if target.updated_at and target.updated_at.tzinfo is None:
        target.updated_at = target.updated_at.replace(tzinfo=timezone.utc)  # type: ignore[assignment]


event.listen(UserCredential, "load", _normalize_credential)
event.listen(UserCredential, "refresh", _normalize_credential)


@event.listens_for(UserCredential.expires_at, "set", retval=True)
@event.listens_for(UserCredential.rotated_at, "set", retval=True)
@event.listens_for(UserCredential.created_at, "set", retval=True)
@event.listens_for(UserCredential.updated_at, "set", retval=True)
def _coerce_credential_dt(
    _target: UserCredential, value: datetime | None, *_: object, **__: object
) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
