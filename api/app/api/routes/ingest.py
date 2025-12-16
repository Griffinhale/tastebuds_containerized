from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schema.ingest import IngestRequest, IngestResponse
from app.schema.media import MediaItemDetail
from app.services import media_service

router = APIRouter()


@router.post("/{source}", response_model=IngestResponse)
async def ingest_media(
    source: str,
    payload: IngestRequest,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> IngestResponse:
    identifier = payload.external_id or payload.url
    if not identifier:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Identifier required")
    media_item = await media_service.ingest_from_source(
        session, source=source, identifier=identifier, force_refresh=payload.force_refresh
    )
    hydrated = await media_service.get_media_with_sources(session, media_item.id)
    return IngestResponse(
        media_item=MediaItemDetail.model_validate(hydrated or media_item),
        source_name=source,
    )
