"""Taste profile aggregation service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.media import MediaItem, UserItemLog, UserItemState
from app.models.menu import Course, CourseItem, Menu
from app.models.tagging import MediaItemTag, Tag
from app.models.user import UserTasteProfile

DEFAULT_REFRESH_HOURS = 24


async def get_or_build_profile(
    session: AsyncSession, user_id: uuid.UUID, *, force_refresh: bool = False
) -> UserTasteProfile:
    """Return a cached taste profile or refresh it."""
    result = await session.execute(select(UserTasteProfile).where(UserTasteProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    refresh_hours = getattr(settings, "taste_profile_refresh_hours", DEFAULT_REFRESH_HOURS)
    if profile and not force_refresh:
        if refresh_hours <= 0:
            return profile
        cutoff = datetime.utcnow() - timedelta(hours=refresh_hours)
        if profile.generated_at and profile.generated_at >= cutoff:
            return profile

    data = await _build_profile_payload(session, user_id)
    now = datetime.utcnow()
    if profile:
        profile.profile = data
        profile.generated_at = now
    else:
        profile = UserTasteProfile(user_id=user_id, profile=data, generated_at=now)
        session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return profile


async def _build_profile_payload(session: AsyncSession, user_id: uuid.UUID) -> dict:
    """Aggregate taste signals from logs, tags, and menus."""
    state_ids = await session.execute(
        select(UserItemState.media_item_id).where(UserItemState.user_id == user_id)
    )
    log_ids = await session.execute(select(UserItemLog.media_item_id).where(UserItemLog.user_id == user_id))
    menu_item_ids = await session.execute(
        select(CourseItem.media_item_id)
        .join(Course)
        .join(Menu)
        .where(Menu.owner_id == user_id)
    )

    media_ids = set(state_ids.scalars().all()) | set(log_ids.scalars().all()) | set(menu_item_ids.scalars().all())

    media_type_counts: dict[str, int] = {}
    if media_ids:
        media_counts = await session.execute(
            select(MediaItem.media_type, func.count())
            .where(MediaItem.id.in_(list(media_ids)))
            .group_by(MediaItem.media_type)
        )
        media_type_counts = {row[0].value: row[1] for row in media_counts.all()}

    menu_counts = await session.execute(
        select(func.count(Menu.id)).where(Menu.owner_id == user_id)
    )
    course_counts = await session.execute(
        select(func.count(Course.id)).join(Menu).where(Menu.owner_id == user_id)
    )
    item_counts = await session.execute(
        select(func.count(CourseItem.id))
        .join(Course)
        .join(Menu)
        .where(Menu.owner_id == user_id)
    )

    menu_media_counts = await session.execute(
        select(MediaItem.media_type, func.count())
        .join(CourseItem, CourseItem.media_item_id == MediaItem.id)
        .join(Course, Course.id == CourseItem.course_id)
        .join(Menu, Menu.id == Course.menu_id)
        .where(Menu.owner_id == user_id)
        .group_by(MediaItem.media_type)
    )
    menu_media_type_counts = {row[0].value: row[1] for row in menu_media_counts.all()}

    tag_counts: list[dict[str, int | str]] = []
    if media_ids:
        tag_results = await session.execute(
            select(Tag.name, func.count(MediaItemTag.id))
            .join(MediaItemTag, MediaItemTag.tag_id == Tag.id)
            .where(
                MediaItemTag.media_item_id.in_(list(media_ids)),
                or_(Tag.owner_id == user_id, Tag.owner_id.is_(None)),
            )
            .group_by(Tag.name)
            .order_by(func.count(MediaItemTag.id).desc())
            .limit(10)
        )
        tag_counts = [{"name": row[0], "count": row[1]} for row in tag_results.all()]

    log_counts = await session.execute(
        select(UserItemLog.log_type, func.count()).where(UserItemLog.user_id == user_id).group_by(UserItemLog.log_type)
    )
    log_totals = {row[0].value: row[1] for row in log_counts.all()}

    minutes_sum = await session.execute(
        select(func.coalesce(func.sum(UserItemLog.minutes_spent), 0)).where(UserItemLog.user_id == user_id)
    )

    favorite_count = await session.execute(
        select(func.count(UserItemState.id)).where(
            UserItemState.user_id == user_id,
            UserItemState.favorite.is_(True),
        )
    )

    return {
        "summary": {
            "menus": int(menu_counts.scalar_one() or 0),
            "courses": int(course_counts.scalar_one() or 0),
            "items": int(item_counts.scalar_one() or 0),
            "favorites": int(favorite_count.scalar_one() or 0),
            "minutes_spent": int(minutes_sum.scalar_one() or 0),
        },
        "media_type_counts": media_type_counts,
        "menu_media_type_counts": menu_media_type_counts,
        "top_tags": tag_counts,
        "log_counts": log_totals,
        "signals": {
            "media_items": len(media_ids),
            "logs": int(sum(log_totals.values())),
        },
    }
