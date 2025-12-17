"""Import all models here for Alembic autogenerate."""

from app.db.base_class import Base
from app.models import auth, media, menu, tagging, user  # noqa: F401

__all__ = ["Base"]
