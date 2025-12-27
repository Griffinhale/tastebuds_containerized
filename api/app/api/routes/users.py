"""User endpoints for profiles and media state tracking."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.media import UserItemLogType
from app.models.user import User
from app.schema.library import LibraryOverview
from app.schema.media import (
    UserItemLogCreate,
    UserItemLogRead,
    UserItemLogUpdate,
    UserItemStateRead,
    UserItemStateUpdate,
)
from app.schema.user import UserRead
from app.services import library_service, user_log_service, user_state_service

router = APIRouter()


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    """Return the current authenticated user."""
    return current_user


@router.get("/me/states", response_model=list[UserItemStateRead])
async def list_states(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """List media states for the current user."""
    return await user_state_service.list_states(session, current_user.id)


@router.put("/me/states/{media_item_id}", response_model=UserItemStateRead)
async def upsert_state(
    media_item_id: uuid.UUID,
    payload: UserItemStateUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Create or update a media state for the current user."""
    try:
        state = await user_state_service.upsert_state(session, current_user.id, media_item_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return state


@router.get("/me/library", response_model=LibraryOverview)
async def read_library(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> LibraryOverview:
    """Return the current user's library snapshot."""
    return await library_service.get_library_overview(session, current_user.id)


@router.get("/me/logs", response_model=list[UserItemLogRead])
async def list_logs(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    media_item_id: uuid.UUID | None = None,
    log_type: UserItemLogType | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[UserItemLogRead]:
    """List log entries for the current user."""
    return await user_log_service.list_logs(
        session,
        current_user.id,
        media_item_id=media_item_id,
        log_type=log_type,
        limit=limit,
        offset=offset,
    )


@router.post("/me/logs", response_model=UserItemLogRead, status_code=status.HTTP_201_CREATED)
async def create_log(
    payload: UserItemLogCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserItemLogRead:
    """Create a log entry for the current user."""
    return await user_log_service.create_log(session, current_user.id, payload)


@router.patch("/me/logs/{log_id}", response_model=UserItemLogRead)
async def update_log(
    log_id: uuid.UUID,
    payload: UserItemLogUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserItemLogRead:
    """Update a log entry for the current user."""
    log = await user_log_service.get_log(session, current_user.id, log_id)
    return await user_log_service.update_log(session, log, payload)


@router.delete(
    "/me/logs/{log_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_log(
    log_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Delete a log entry for the current user."""
    log = await user_log_service.get_log(session, current_user.id, log_id)
    await user_log_service.delete_log(session, log)
