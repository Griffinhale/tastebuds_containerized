"""User endpoints for profiles and media state tracking."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schema.media import UserItemStateRead, UserItemStateUpdate
from app.schema.user import UserRead
from app.services import user_state_service

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
