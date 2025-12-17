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
    CourseItemReorder,
    CourseItemRead,
    CourseRead,
    MenuCreate,
    MenuRead,
    MenuUpdate,
)
from app.services import menu_service

router = APIRouter()


@router.get("", response_model=list[MenuRead])
async def list_menus(
    session: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[Menu]:
    return await menu_service.list_menus_for_user(session, current_user.id)


@router.post("", response_model=MenuRead, status_code=status.HTTP_201_CREATED)
async def create_menu_endpoint(
    payload: MenuCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Menu:
    return await menu_service.create_menu(session, current_user.id, payload)


@router.get("/{menu_id}", response_model=MenuRead)
async def get_menu_endpoint(
    menu_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Menu:
    return await menu_service.get_menu(session, menu_id, owner_id=current_user.id)


@router.patch("/{menu_id}", response_model=MenuRead)
async def update_menu_endpoint(
    menu_id: uuid.UUID,
    payload: MenuUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Menu:
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
    menu = await menu_service.get_menu(session, menu_id, owner_id=current_user.id)
    await menu_service.delete_menu(session, menu)


@router.post("/{menu_id}/courses", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
async def add_course_endpoint(
    menu_id: uuid.UUID,
    payload: CourseCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Course:
    menu = await menu_service.get_menu(session, menu_id, owner_id=current_user.id)
    return await menu_service.add_course(session, menu, payload)


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
    menu = await menu_service.get_menu(session, menu_id, owner_id=current_user.id)
    course = await menu_service.get_course(session, course_id, current_user.id)
    if course.menu_id != menu.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found in menu")
    return await menu_service.add_course_item(session, course, payload)


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
    menu = await menu_service.get_menu(session, menu_id, owner_id=current_user.id)
    course = await menu_service.get_course(session, course_id, current_user.id)
    if course.menu_id != menu.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found in menu")
    return await menu_service.reorder_course_items(session, course, payload.item_ids)
