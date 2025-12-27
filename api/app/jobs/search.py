"""RQ jobs for external search fan-out and serialization."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Iterable

from app.db.session import async_session
from app.models.media import MediaType
from app.schema.search import SearchResultItem
from app.services import media_service


def _deserialize_media_types(values: Iterable[str] | None) -> set[MediaType] | None:
    """Convert string media type values to enums, skipping invalid entries."""
    if not values:
        return None
    media_types: set[MediaType] = set()
    for value in values:
        try:
            media_types.add(MediaType(value))
        except ValueError:
            continue
    return media_types or None


def _deserialize_existing_keys(keys: Iterable[Iterable[str]] | None) -> set[media_service.DedupeKey] | None:
    """Convert serialized dedupe keys back into tuples."""
    if not keys:
        return None
    return {tuple(key) for key in keys if key}


def serialize_external_outcome(outcome: media_service.ExternalSearchOutcome) -> dict[str, Any]:
    """Serialize external search outcomes for queue transport."""
    return {
        "hits": [{"source": hit.source, "item": hit.item.model_dump()} for hit in outcome.hits],
        "counts": outcome.counts,
        "deduped_counts": outcome.deduped_counts,
        "timings_ms": {
            source: {"search_ms": timing.search_ms, "fetch_ms": timing.fetch_ms}
            for source, timing in outcome.timings_ms.items()
        },
    }


def deserialize_external_outcome(payload: dict[str, Any] | None) -> media_service.ExternalSearchOutcome:
    """Deserialize queued search outcomes back into rich objects."""
    payload = payload or {}
    timings = {
        source: media_service.ExternalSourceTiming(
            search_ms=data.get("search_ms"), fetch_ms=data.get("fetch_ms", 0.0)
        )
        for source, data in (payload.get("timings_ms") or {}).items()
    }
    hits = [
        media_service.ExternalSearchHit(
            source=entry.get("source", "external"),
            item=SearchResultItem.model_validate(entry.get("item") or {}),
        )
        for entry in (payload.get("hits") or [])
    ]
    return media_service.ExternalSearchOutcome(
        hits=hits,
        counts=payload.get("counts") or {},
        deduped_counts=payload.get("deduped_counts") or {},
        timings_ms=timings,
    )


def fanout_external_search_job(
    *,
    query: str,
    user_id: str,
    per_source: int = 1,
    sources: list[str] | None = None,
    allowed_media_types: list[str] | None = None,
    existing_keys: list[list[str]] | None = None,
) -> dict[str, Any]:
    """Run external search fan-out inside a worker process."""
    async def _run() -> dict[str, Any]:
        async with async_session() as session:
            outcome = await media_service.search_external_sources(
                session,
                query=query,
                user_id=uuid.UUID(user_id),
                per_source=per_source,
                sources=sources,
                allowed_media_types=_deserialize_media_types(allowed_media_types),
                existing_keys=_deserialize_existing_keys(existing_keys),
            )
            return serialize_external_outcome(outcome)

    return asyncio.run(_run())
