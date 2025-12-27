"""User log CRUD helpers with state synchronization."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.media import MediaItem, UserItemLog, UserItemLogType, UserItemState, UserItemStatus
from app.schema.media import UserItemLogCreate, UserItemLogUpdate


async def list_logs(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    media_item_id: uuid.UUID | None = None,
    log_type: UserItemLogType | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[UserItemLog]:
    """List log entries for a user with optional filters."""
    query = (
        select(UserItemLog)
        .options(selectinload(UserItemLog.media_item))
        .where(UserItemLog.user_id == user_id)
    )
    if media_item_id:
        query = query.where(UserItemLog.media_item_id == media_item_id)
    if log_type:
        query = query.where(UserItemLog.log_type == log_type)
    query = query.order_by(UserItemLog.logged_at.desc(), UserItemLog.created_at.desc())
    result = await session.execute(query.offset(offset).limit(limit))
    return result.scalars().all()


async def get_log(session: AsyncSession, user_id: uuid.UUID, log_id: uuid.UUID) -> UserItemLog:
    """Fetch a single log entry scoped to the user."""
    result = await session.execute(
        select(UserItemLog)
        .options(selectinload(UserItemLog.media_item))
        .where(UserItemLog.user_id == user_id, UserItemLog.id == log_id)
    )
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log entry not found")
    return log


async def create_log(session: AsyncSession, user_id: uuid.UUID, payload: UserItemLogCreate) -> UserItemLog:
    """Create a log entry and update state when appropriate."""
    media = await session.get(MediaItem, payload.media_item_id)
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found")

    log = UserItemLog(
        user_id=user_id,
        media_item_id=payload.media_item_id,
        log_type=payload.log_type,
        notes=payload.notes,
        minutes_spent=payload.minutes_spent,
        progress_percent=payload.progress_percent,
        goal_target=payload.goal_target,
        goal_due_on=payload.goal_due_on,
        logged_at=payload.logged_at or datetime.utcnow(),
    )
    session.add(log)
    await _sync_state_from_log(session, user_id, log)
    await session.commit()
    await session.refresh(log)
    return log


async def update_log(session: AsyncSession, log: UserItemLog, payload: UserItemLogUpdate) -> UserItemLog:
    """Update a log entry and re-evaluate state if needed."""
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(log, field, value)

    if updates:
        await _sync_state_from_log(session, log.user_id, log)
    await session.commit()
    await session.refresh(log)
    return log


async def delete_log(session: AsyncSession, log: UserItemLog) -> None:
    """Remove a log entry."""
    await session.delete(log)
    await session.commit()


async def _sync_state_from_log(session: AsyncSession, user_id: uuid.UUID, log: UserItemLog) -> None:
    """Apply log-derived status updates without overriding explicit drops."""
    result = await session.execute(
        select(UserItemState).where(
            UserItemState.user_id == user_id,
            UserItemState.media_item_id == log.media_item_id,
        )
    )
    state = result.scalar_one_or_none()

    if log.log_type == UserItemLogType.GOAL:
        if state is None:
            state = UserItemState(
                user_id=user_id,
                media_item_id=log.media_item_id,
                status=UserItemStatus.WANT,
            )
            session.add(state)
        return

    if log.log_type == UserItemLogType.FINISHED:
        if state is None:
            state = UserItemState(
                user_id=user_id,
                media_item_id=log.media_item_id,
                status=UserItemStatus.CONSUMED,
            )
            session.add(state)
        else:
            state.status = UserItemStatus.CONSUMED
        state.finished_at = log.logged_at
        if not state.started_at:
            state.started_at = log.logged_at
        return

    if log.log_type in (UserItemLogType.STARTED, UserItemLogType.PROGRESS):
        if state is None:
            state = UserItemState(
                user_id=user_id,
                media_item_id=log.media_item_id,
                status=UserItemStatus.CONSUMING,
            )
            session.add(state)
        elif state.status not in (UserItemStatus.DROPPED, UserItemStatus.CONSUMED):
            state.status = UserItemStatus.CONSUMING
        if not state.started_at:
            state.started_at = log.logged_at
