from __future__ import annotations

from datetime import date


def parse_date(value: str | None) -> date | None:
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
