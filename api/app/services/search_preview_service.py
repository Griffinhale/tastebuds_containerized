from __future__ import annotations

import math
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.ingestion.base import ConnectorResult
from app.models.search_preview import ExternalSearchPreview, UserExternalSearchQuota


def _serialize_result(result: ConnectorResult) -> dict[str, Any]:
    return {
        "source_url": result.source_url,
        "raw_payload": result.raw_payload,
        "extensions": result.extensions,
    }


async def cache_connector_result(
    session: AsyncSession, user_id: uuid.UUID, result: ConnectorResult
) -> ExternalSearchPreview:
    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=settings.external_search_preview_ttl_seconds)
    stmt = (
        select(ExternalSearchPreview)
        .where(
            ExternalSearchPreview.user_id == user_id,
            ExternalSearchPreview.source_name == result.source_name,
            ExternalSearchPreview.external_id == result.source_id,
        )
        .limit(1)
    )
    existing = await session.scalar(stmt)
    serialized_payload = _serialize_result(result)
    metadata = result.metadata or {}
    if existing:
        existing.media_type = result.media_type
        existing.title = result.title
        existing.description = result.description
        existing.release_date = result.release_date
        existing.cover_image_url = result.cover_image_url
        existing.canonical_url = result.canonical_url
        existing.metadata_payload = metadata
        existing.raw_payload = serialized_payload
        existing.expires_at = expires_at
        preview = existing
    else:
        preview = ExternalSearchPreview(
            user_id=user_id,
            source_name=result.source_name,
            external_id=result.source_id,
            media_type=result.media_type,
            title=result.title,
            description=result.description,
            release_date=result.release_date,
            cover_image_url=result.cover_image_url,
            canonical_url=result.canonical_url,
            metadata_payload=metadata,
            raw_payload=serialized_payload,
            expires_at=expires_at,
        )
        session.add(preview)
    await session.commit()
    await session.refresh(preview)
    return preview


async def prune_expired_previews(session: AsyncSession) -> None:
    now = datetime.utcnow()
    await session.execute(delete(ExternalSearchPreview).where(ExternalSearchPreview.expires_at <= now))
    await session.commit()


async def enforce_search_quota(session: AsyncSession, user_id: uuid.UUID) -> None:
    window_seconds = max(1, settings.external_search_quota_window_seconds)
    now = datetime.utcnow()
    bucket_start = math.floor(now.timestamp() / window_seconds) * window_seconds
    window_start = datetime.utcfromtimestamp(bucket_start)
    quota = await session.get(UserExternalSearchQuota, user_id)
    if not quota:
        quota = UserExternalSearchQuota(user_id=user_id, window_start=window_start, count=1)
        session.add(quota)
        await session.commit()
        return
    if quota.window_start == window_start:
        if quota.count >= settings.external_search_quota_max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"External search quota exceeded ({settings.external_search_quota_max_requests} requests per {window_seconds}s)",
            )
        quota.count += 1
    else:
        quota.window_start = window_start
        quota.count = 1
    await session.commit()
