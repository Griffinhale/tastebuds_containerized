"""Menu endpoints for CRUD operations on menus and courses."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.menu import Course, Menu
from app.models.user import User
from app.schema.menu import (
    CourseCreate,
    CourseItemCreate,
    CourseItemRead,
    CourseItemReorder,
    CourseItemUpdate,
    CourseRead,
    CourseUpdate,
    MenuCreate,
    MenuForkCreate,
    MenuItemPairingCreate,
    MenuItemPairingRead,
    MenuLineageRead,
    MenuRead,
    MenuShareTokenCreate,
    MenuShareTokenRead,
    MenuUpdate,
)
from app.services import menu_service

router = APIRouter()


@router.get("", response_model=list[MenuRead])
async def list_menus(
    session: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[Menu]:
    """List menus for the current user."""
    return await menu_service.list_menus_for_user(session, current_user.id)


@router.post("", response_model=MenuRead, status_code=status.HTTP_201_CREATED)
async def create_menu_endpoint(
    payload: MenuCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Menu:
    """Create a menu for the current user."""
    return await menu_service.create_menu(session, current_user.id, payload)


@router.get("/{menu_id}", response_model=MenuRead)
async def get_menu_endpoint(
    menu_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Menu:
    """Fetch a menu by ID."""
    return await menu_service.get_menu(session, menu_id, owner_id=current_user.id)


@router.patch("/{menu_id}", response_model=MenuRead)
async def update_menu_endpoint(
    menu_id: uuid.UUID,
    payload: MenuUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Menu:
    """Update menu metadata."""
    menu = await menu_service.get_menu(session, menu_id, owner_id=current_user.id)
    return await menu_service.update_menu(session, menu, payload)


@router.delete(
    "/{menu_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def delete_menu_endpoint(
    menu_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a menu and its courses."""
    menu = await menu_service.get_menu(session, menu_id, owner_id=current_user.id)
    await menu_service.delete_menu(session, menu)


@router.post("/{menu_id}/courses", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
async def add_course_endpoint(
    menu_id: uuid.UUID,
    payload: CourseCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Course:
    """Add a new course to a menu."""
    menu = await menu_service.get_menu(session, menu_id, owner_id=current_user.id)
    return await menu_service.add_course(session, menu, payload)


@router.patch("/{menu_id}/courses/{course_id}", response_model=CourseRead)
async def update_course_endpoint(
    menu_id: uuid.UUID,
    course_id: uuid.UUID,
    payload: CourseUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Course:
    """Update course metadata."""
    menu = await menu_service.get_menu(session, menu_id, owner_id=current_user.id)
    course = await menu_service.get_course(session, course_id, current_user.id)
    if course.menu_id != menu.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found in menu")
    return await menu_service.update_course(session, course, payload)


@router.delete(
    "/{menu_id}/courses/{course_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def delete_course_endpoint(
    menu_id: uuid.UUID,
    course_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a course from a menu."""
    menu = await menu_service.get_menu(session, menu_id, owner_id=current_user.id)
    course = await menu_service.get_course(session, course_id, current_user.id)
    if course.menu_id != menu.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found in menu")
    await menu_service.delete_course(session, course)


@router.post(
    "/{menu_id}/courses/{course_id}/items",
    response_model=CourseItemRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_course_item_endpoint(
    menu_id: uuid.UUID,
    course_id: uuid.UUID,
    payload: CourseItemCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a media item to a course."""
    menu = await menu_service.get_menu(session, menu_id, owner_id=current_user.id)
    course = await menu_service.get_course(session, course_id, current_user.id)
    if course.menu_id != menu.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found in menu")
    return await menu_service.add_course_item(session, course, payload)


@router.patch("/{menu_id}/course-items/{item_id}", response_model=CourseItemRead)
async def update_course_item_endpoint(
    menu_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: CourseItemUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CourseItemRead:
    """Update course item annotations."""
    menu = await menu_service.get_menu(session, menu_id, owner_id=current_user.id)
    course_item = await menu_service.get_course_item(session, item_id, current_user.id)
    if course_item.course.menu_id != menu.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found in menu")
    return await menu_service.update_course_item(session, course_item, payload)


@router.delete(
    "/{menu_id}/course-items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def delete_course_item_endpoint(
    menu_id: uuid.UUID,
    item_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a course item from a menu."""
    menu = await menu_service.get_menu(session, menu_id, owner_id=current_user.id)
    course_item = await menu_service.get_course_item(session, item_id, current_user.id)
    if course_item.course.menu_id != menu.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found in menu")
    await menu_service.delete_course_item(session, course_item)


@router.post(
    "/{menu_id}/courses/{course_id}/reorder-items",
    response_model=CourseRead,
)
async def reorder_course_items_endpoint(
    menu_id: uuid.UUID,
    course_id: uuid.UUID,
    payload: CourseItemReorder,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Course:
    """Reorder items within a course."""
    menu = await menu_service.get_menu(session, menu_id, owner_id=current_user.id)
    course = await menu_service.get_course(session, course_id, current_user.id)
    if course.menu_id != menu.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found in menu")
    return await menu_service.reorder_course_items(session, course, payload.item_ids)


@router.post("/{menu_id}/fork", response_model=MenuRead, status_code=status.HTTP_201_CREATED)
async def fork_menu_endpoint(
    menu_id: uuid.UUID,
    payload: MenuForkCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Menu:
    """Fork a menu into a new draft."""
    source_menu = await menu_service.get_menu_for_fork(session, menu_id, current_user.id)
    return await menu_service.fork_menu(session, source_menu, current_user.id, payload)


@router.get("/{menu_id}/lineage", response_model=MenuLineageRead)
async def read_menu_lineage(
    menu_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MenuLineageRead:
    """Return lineage metadata for a menu."""
    menu = await menu_service.get_menu(session, menu_id, owner_id=current_user.id)
    source_menu, source_note, forks = await menu_service.get_menu_lineage_summary(
        session, menu.id, include_private=True
    )
    source_payload = None
    if source_menu:
        source_payload = {"menu": source_menu, "note": source_note}
    return MenuLineageRead(source_menu=source_payload, forked_menus=forks, fork_count=len(forks))


@router.get("/{menu_id}/pairings", response_model=list[MenuItemPairingRead])
async def list_pairings_endpoint(
    menu_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MenuItemPairingRead]:
    """List narrative pairings for a menu."""
    return await menu_service.list_pairings(session, menu_id, current_user.id)


@router.post("/{menu_id}/pairings", response_model=MenuItemPairingRead, status_code=status.HTTP_201_CREATED)
async def create_pairing_endpoint(
    menu_id: uuid.UUID,
    payload: MenuItemPairingCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MenuItemPairingRead:
    """Create a narrative pairing between two items."""
    menu = await menu_service.get_menu(session, menu_id, owner_id=current_user.id)
    return await menu_service.create_pairing(session, menu, payload)


@router.delete(
    "/{menu_id}/pairings/{pairing_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def delete_pairing_endpoint(
    menu_id: uuid.UUID,
    pairing_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a narrative pairing."""
    pairing = await menu_service.get_pairing(session, pairing_id, current_user.id)
    if pairing.menu_id != menu_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pairing not found")
    await menu_service.delete_pairing(session, pairing)


@router.get("/{menu_id}/share-tokens", response_model=list[MenuShareTokenRead])
async def list_share_tokens_endpoint(
    menu_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MenuShareTokenRead]:
    """List draft share tokens for a menu."""
    return await menu_service.list_share_tokens(session, menu_id, current_user.id)


@router.post("/{menu_id}/share-tokens", response_model=MenuShareTokenRead, status_code=status.HTTP_201_CREATED)
async def create_share_token_endpoint(
    menu_id: uuid.UUID,
    payload: MenuShareTokenCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MenuShareTokenRead:
    """Create a draft share token for a menu."""
    menu = await menu_service.get_menu(session, menu_id, owner_id=current_user.id)
    return await menu_service.create_share_token(
        session, menu, created_by=current_user.id, expires_at=payload.expires_at
    )


@router.delete(
    "/{menu_id}/share-tokens/{token_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def revoke_share_token_endpoint(
    menu_id: uuid.UUID,
    token_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Revoke a draft share token."""
    await menu_service.revoke_share_token(session, token_id, current_user.id, menu_id=menu_id)
