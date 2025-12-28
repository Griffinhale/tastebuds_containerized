"""Import all models here for Alembic autogenerate."""

from app.db.base_class import Base
from app.models import (  # noqa: F401
    auth,
    automation,
    credential,
    integration,
    media,
    menu,
    search_preview,
    tagging,
    user,
)

__all__ = ["Base"]
