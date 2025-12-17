from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media import MediaItem, UserItemState
from app.schema.media import UserItemStateUpdate


async def list_states(session: AsyncSession, user_id: uuid.UUID) -> list[UserItemState]:
    result = await session.execute(select(UserItemState).where(UserItemState.user_id == user_id))
    return result.scalars().all()


async def upsert_state(
    session: AsyncSession,
    user_id: uuid.UUID,
    media_item_id: uuid.UUID,
    payload: UserItemStateUpdate,
) -> UserItemState:
    media = await session.get(MediaItem, media_item_id)
    if not media:
        raise ValueError("Media item not found")
    stmt = select(UserItemState).where(UserItemState.user_id == user_id, UserItemState.media_item_id == media_item_id)
    result = await session.execute(stmt)
    state = result.scalar_one_or_none()
    if state:
        state.status = payload.status
        state.rating = payload.rating
        state.favorite = payload.favorite
        state.notes = payload.notes
        state.started_at = payload.started_at
        state.finished_at = payload.finished_at
    else:
        state = UserItemState(
            user_id=user_id,
            media_item_id=media_item_id,
            status=payload.status,
            rating=payload.rating,
            favorite=payload.favorite,
            notes=payload.notes,
            started_at=payload.started_at,
            finished_at=payload.finished_at,
        )
        session.add(state)
    await session.commit()
    await session.refresh(state)
    return state
