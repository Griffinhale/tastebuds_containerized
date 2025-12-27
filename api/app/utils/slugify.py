"""Slug helpers for menu identifiers."""

from slugify import slugify


def menu_slug(value: str, suffix: str | None = None) -> str:
    """Slugify menu titles with an optional suffix."""
    base = slugify(value)
    if suffix:
        return f"{base}-{slugify(suffix)}"
    return base
