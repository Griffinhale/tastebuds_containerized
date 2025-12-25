"""Import all models here for Alembic autogenerate."""

from app.db.base_class import Base
from app.models import auth, credential, media, menu, search_preview, tagging, user  # noqa: F401

__all__ = ["Base"]
