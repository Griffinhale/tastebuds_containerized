"""Authentication-related request/response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schema.user import UserRead


class TokenPair(BaseModel):
    """Access and refresh token bundle returned after auth."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserRead


class SessionRead(BaseModel):
    """Session metadata for listing and revocation views."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
    revoked_reason: str | None = None
    replaced_by_token_id: UUID | None = None
    is_active: bool = Field(default=False)
    is_current: bool = Field(default=False)
