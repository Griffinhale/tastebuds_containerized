from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.tagging import Tag
from app.schema.tag import TagAssignmentPayload, TagCreate, TagRead
from app.services import tag_service

router = APIRouter()


@router.get("", response_model=list[TagRead])
async def list_tags(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TagRead]:
    tags = await tag_service.list_tags(session, current_user.id)
    return [TagRead.model_validate(tag) for tag in tags]


@router.post("", response_model=TagRead, status_code=status.HTTP_201_CREATED)
async def create_tag_endpoint(
    payload: TagCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TagRead:
    try:
        tag = await tag_service.create_tag(session, current_user.id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return TagRead.model_validate(tag)


@router.delete(
    "/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def delete_tag_endpoint(
    tag_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        await tag_service.delete_tag(session, current_user.id, tag_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/media/{media_item_id}", response_model=list[TagRead])
async def list_media_tags_endpoint(
    media_item_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TagRead]:
    tags = await tag_service.list_media_tags(session, current_user.id, media_item_id)
    return [TagRead.model_validate(tag) for tag in tags]


@router.post("/{tag_id}/media", response_model=TagRead, status_code=status.HTTP_201_CREATED)
async def add_tag_to_media_endpoint(
    tag_id: uuid.UUID,
    payload: TagAssignmentPayload,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TagRead:
    try:
        await tag_service.add_tag_to_media(session, current_user.id, tag_id, payload.media_item_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    tag = await session.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    return TagRead.model_validate(tag)


@router.delete(
    "/{tag_id}/media/{media_item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def remove_tag_from_media_endpoint(
    tag_id: uuid.UUID,
    media_item_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        await tag_service.remove_tag_from_media(session, current_user.id, tag_id, media_item_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
