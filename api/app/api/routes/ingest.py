"""Ingestion endpoints for external previews."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.jobs.ingestion import ingest_media_job
from app.models.user import User
from app.schema.ingest import IngestRequest, IngestResponse
from app.schema.media import MediaItemDetail
from app.services import media_service
from app.services.task_queue import task_queue

router = APIRouter()


@router.post("/{source}", response_model=IngestResponse)
async def ingest_media(
    source: str,
    payload: IngestRequest,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> IngestResponse:
    """Ingest an external item and return the stored media record."""
    identifier = payload.external_id or payload.url
    if not identifier:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Identifier required")

    async def _fallback() -> dict:
        # Inline fallback when worker queue is unavailable.
        media_item = await media_service.ingest_from_source(
            session, source=source, identifier=identifier, force_refresh=payload.force_refresh
        )
        hydrated = await media_service.get_media_with_sources(session, media_item.id)
        detail = MediaItemDetail.model_validate(hydrated or media_item)
        return {"media_item": detail.model_dump(), "source_name": source}

    outcome = await task_queue.enqueue_or_run(
        ingest_media_job,
        fallback=_fallback,
        queue_name="ingestion",
        timeout_seconds=90,
        description=f"ingest:{source}",
        source=source,
        identifier=identifier,
        force_refresh=payload.force_refresh,
    )
    if not outcome or "media_item" not in outcome:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Ingestion job failed")
    media_detail = MediaItemDetail.model_validate(outcome["media_item"])
    return IngestResponse(media_item=media_detail, source_name=outcome.get("source_name", source))
