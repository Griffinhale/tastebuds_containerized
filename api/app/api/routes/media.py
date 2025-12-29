"""Media endpoints for availability management."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schema.media import (
    AvailabilitySummaryItem,
    AvailabilitySummaryRequest,
    MediaAvailabilityRead,
    MediaAvailabilityUpsert,
    MediaItemDetail,
)
from app.services import availability_service, media_service

router = APIRouter()


@router.get("/media/{media_item_id}/availability", response_model=list[MediaAvailabilityRead])
async def list_media_availability(
    media_item_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> list[MediaAvailabilityRead]:
    """List availability entries for a media item."""
    return await availability_service.list_availability(session, media_item_id)


@router.get("/media/{media_item_id}", response_model=MediaItemDetail)
async def get_media_detail(
    media_item_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> MediaItemDetail:
    """Return a media item with attached source records."""
    media = await media_service.get_media_with_sources(session, media_item_id)
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found")
    return MediaItemDetail.model_validate(media)


@router.put("/media/{media_item_id}/availability", response_model=list[MediaAvailabilityRead])
async def upsert_media_availability(
    media_item_id: uuid.UUID,
    payload: list[MediaAvailabilityUpsert],
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MediaAvailabilityRead]:
    """Upsert availability entries for a media item."""
    media = await media_service.get_media_by_id(session, media_item_id)
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found")
    return await availability_service.upsert_availability(session, media_item_id, payload)


@router.post("/media/availability/summary", response_model=list[AvailabilitySummaryItem])
async def summarize_availability(
    payload: AvailabilitySummaryRequest,
    session: AsyncSession = Depends(get_db),
) -> list[AvailabilitySummaryItem]:
    """Return aggregated availability summaries for media IDs."""
    summaries = await availability_service.get_availability_summary(session, payload.media_item_ids)
    return [
        AvailabilitySummaryItem(media_item_id=media_item_id, **summary.model_dump())
        for media_item_id, summary in summaries.items()
    ]
