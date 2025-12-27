"""Shared schema base classes for API responses."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class ORMModel(BaseModel):
    """Base model that supports orm_mode for SQLAlchemy."""

    model_config = {"from_attributes": True}


class Timestamped(ORMModel):
    """Common timestamps for resource schemas."""
    id: UUID
    created_at: datetime
    updated_at: datetime


class Dated(ORMModel):
    """Optional release date container for dated media."""
    id: UUID
    release_date: date | None = None
