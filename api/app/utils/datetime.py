"""Datetime parsing helpers for ingestion payloads."""

from __future__ import annotations

from datetime import date


def parse_date(value: str | None) -> date | None:
    """Parse YYYY, YYYY-MM, or YYYY-MM-DD strings into dates."""
    if not value:
        return None
    try:
        if len(value) == 4:
            return date.fromisoformat(f"{value}-01-01")
        if len(value) == 7:
            return date.fromisoformat(f"{value}-01")
        return date.fromisoformat(value)
    except ValueError:
        return None
