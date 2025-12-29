"""Preview detail endpoints for external search results."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.search_preview import ExternalSearchPreview
from app.models.user import User
from app.schema.preview import ExternalPreviewDetail

router = APIRouter()


@router.get("/previews/{preview_id}", response_model=ExternalPreviewDetail)
async def get_preview_detail(
    preview_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExternalPreviewDetail:
    """Return preview details for an external search result."""
    preview = await session.get(ExternalSearchPreview, preview_id)
    if not preview or preview.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Preview not found")

    now = datetime.now(timezone.utc)
    if preview.expires_at and preview.expires_at <= now:
        raise HTTPException(status_code=404, detail="Preview expired")

    payload = preview.raw_payload or {}
    extensions = payload.get("extensions") if isinstance(payload, dict) else None
    if not isinstance(extensions, dict):
        extensions = {}

    source_url = payload.get("source_url") if isinstance(payload, dict) else None
    if not isinstance(source_url, str):
        source_url = None

    return ExternalPreviewDetail(
        preview_id=preview.id,
        media_type=preview.media_type,
        title=preview.title,
        description=preview.description,
        release_date=preview.release_date,
        cover_image_url=preview.cover_image_url,
        canonical_url=preview.canonical_url,
        metadata=preview.metadata_payload,
        source_name=preview.source_name,
        source_id=preview.external_id,
        source_url=source_url,
        preview_expires_at=preview.expires_at,
        book=extensions.get("book"),
        movie=extensions.get("movie"),
        game=extensions.get("game"),
        music=extensions.get("music"),
    )
