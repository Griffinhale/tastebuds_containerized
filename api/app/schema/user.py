"""User request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schema.base import ORMModel


class UserCreate(BaseModel):
    """Payload for registering a new user."""
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str | None = None


class UserLogin(BaseModel):
    """Payload for user login requests."""
    email: EmailStr
    password: str


class UserRead(ORMModel):
    """User profile fields exposed in API responses."""
    id: UUID
    email: EmailStr
    display_name: str | None = None
    created_at: datetime
