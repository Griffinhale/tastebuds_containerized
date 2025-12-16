from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.media import MediaType
from app.schema.media import MediaItemBase
from app.schema.search import SearchResult
from app.services import media_service

router = APIRouter()


@router.get("", response_model=SearchResult)
async def search(
    q: str = Query(..., min_length=2),
    types: List[MediaType] | None = Query(default=None, alias="types"),
    include_external: bool = Query(default=False),
    session: AsyncSession = Depends(get_db),
) -> SearchResult:
    internal = await media_service.search_media(session, query=q, media_types=types)
    items_by_id: dict[str, MediaItemBase] = {
        str(item.id): MediaItemBase.model_validate(item) for item in internal
    }
    metadata = {"internal_results": len(items_by_id)}
    if include_external:
        external = await media_service.search_external_sources(session, q)
        for item in external:
            items_by_id[str(item.id)] = MediaItemBase.model_validate(item)
        metadata["external_ingested"] = len(external)
        source = "internal+external"
    else:
        source = "internal"
    return SearchResult(results=list(items_by_id.values()), source=source, metadata=metadata)
