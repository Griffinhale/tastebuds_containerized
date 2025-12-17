from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import case, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.media import MediaItem
from app.models.menu import Course, CourseItem, Menu
from app.schema.menu import CourseCreate, CourseItemCreate, MenuCreate, MenuUpdate
from app.utils.slugify import menu_slug


async def list_menus_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[Menu]:
    result = await session.execute(
        select(Menu)
        .execution_options(populate_existing=True)
        .options(selectinload(Menu.courses).selectinload(Course.items).selectinload(CourseItem.media_item))
        .where(Menu.owner_id == user_id)
    )
    return result.scalars().all()


async def get_menu(session: AsyncSession, menu_id: uuid.UUID, *, owner_id: uuid.UUID | None = None) -> Menu:
    query = (
        select(Menu)
        .execution_options(populate_existing=True)
        .options(selectinload(Menu.courses).selectinload(Course.items).selectinload(CourseItem.media_item))
        .where(Menu.id == menu_id)
    )
    if owner_id:
        query = query.where(Menu.owner_id == owner_id)
    result = await session.execute(query)
    menu = result.scalar_one_or_none()
    if not menu:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu not found")
    return menu


async def get_menu_by_slug(session: AsyncSession, slug: str) -> Menu | None:
    result = await session.execute(
        select(Menu)
        .execution_options(populate_existing=True)
        .options(selectinload(Menu.courses).selectinload(Course.items).selectinload(CourseItem.media_item))
        .where(Menu.slug == slug, Menu.is_public.is_(True))
    )
    return result.scalar_one_or_none()


async def create_menu(session: AsyncSession, owner_id: uuid.UUID, payload: MenuCreate) -> Menu:
    slug = await _generate_unique_slug(session, payload.title)
    menu = Menu(
        owner_id=owner_id,
        title=payload.title,
        description=payload.description,
        is_public=payload.is_public,
        slug=slug,
    )
    session.add(menu)
    await session.flush()

    for course_data in payload.courses:
        # Avoid touching relationship attributes directly; they lazily load
        # and would try to emit sync IO inside async contexts.
        await _create_course(session, menu, course_data)

    await session.commit()
    return await _load_menu_with_children(session, menu.id)


async def update_menu(session: AsyncSession, menu: Menu, payload: MenuUpdate) -> Menu:
    if payload.title:
        menu.title = payload.title
    if payload.description is not None:
        menu.description = payload.description
    if payload.is_public is not None:
        menu.is_public = payload.is_public
    await session.commit()
    return await _load_menu_with_children(session, menu.id)


async def delete_menu(session: AsyncSession, menu: Menu) -> None:
    await session.delete(menu)
    await session.commit()


async def add_course(session: AsyncSession, menu: Menu, payload: CourseCreate) -> Course:
    course = await _create_course(session, menu, payload)
    await session.commit()
    return await _load_course_with_items(session, course.id)


async def get_course(session: AsyncSession, course_id: uuid.UUID, owner_id: uuid.UUID) -> Course:
    query = select(Course).join(Menu).where(Course.id == course_id, Menu.owner_id == owner_id)
    result = await session.execute(query)
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return course


async def add_course_item(session: AsyncSession, course: Course, payload: CourseItemCreate) -> CourseItem:
    media = await _get_media(session, payload.media_item_id)
    item = CourseItem(
        course_id=course.id,
        media_item_id=media.id,
        notes=payload.notes,
        position=payload.position,
    )
    session.add(item)
    await session.commit()
    return await _load_course_item_with_media(session, item.id)


async def delete_course(session: AsyncSession, course: Course) -> None:
    await session.delete(course)
    await session.commit()


async def get_course_item(session: AsyncSession, item_id: uuid.UUID, owner_id: uuid.UUID) -> CourseItem:
    query = (
        select(CourseItem)
        .join(Course)
        .join(Menu)
        .options(selectinload(CourseItem.course))
        .where(CourseItem.id == item_id, Menu.owner_id == owner_id)
    )
    result = await session.execute(query)
    course_item = result.scalar_one_or_none()
    if not course_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course item not found")
    return course_item


async def delete_course_item(session: AsyncSession, course_item: CourseItem) -> None:
    await session.delete(course_item)
    await session.commit()


async def reorder_course_items(
    session: AsyncSession,
    course: Course,
    item_ids: list[uuid.UUID],
) -> Course:
    db_course = await _load_course_with_items(session, course.id)
    existing_ids = [item.id for item in db_course.items]
    if sorted(existing_ids) != sorted(item_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item IDs must match the existing course items.",
        )
    if len(item_ids) != len(existing_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Include all existing course item IDs in the reorder payload.",
        )

    if not item_ids:
        return db_course

    whens = [(CourseItem.id == item_id, position) for position, item_id in enumerate(item_ids, start=1)]
    num_items = len(item_ids)
    await session.execute(
        update(CourseItem)
        .where(
            CourseItem.course_id == course.id,
            CourseItem.id.in_(item_ids),
        )
        .values(position=CourseItem.position + num_items)
    )
    await session.execute(
        update(CourseItem)
        .where(
            CourseItem.course_id == course.id,
            CourseItem.id.in_(item_ids),
        )
        .values(position=case(*whens, else_=CourseItem.position))
    )
    await session.commit()
    return await _load_course_with_items(session, course.id)


async def _create_course(session: AsyncSession, menu: Menu, payload: CourseCreate) -> Course:
    course = Course(
        menu_id=menu.id,
        title=payload.title,
        description=payload.description,
        position=payload.position,
    )
    session.add(course)
    await session.flush()
    for item_payload in payload.items:
        media = await _get_media(session, item_payload.media_item_id)
        session.add(
            CourseItem(
                course_id=course.id,
                media_item_id=media.id,
                notes=item_payload.notes,
                position=item_payload.position,
            )
        )
    return course


async def _get_media(session: AsyncSession, media_item_id: uuid.UUID) -> MediaItem:
    result = await session.execute(select(MediaItem).where(MediaItem.id == media_item_id))
    media = result.scalar_one_or_none()
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found")
    return media


async def _generate_unique_slug(session: AsyncSession, title: str) -> str:
    base = menu_slug(title) or "menu"
    slug = base
    counter = 1
    while await _slug_exists(session, slug):
        counter += 1
        slug = f"{base}-{counter}"
    return slug


async def _slug_exists(session: AsyncSession, slug: str) -> bool:
    result = await session.execute(select(Menu).where(Menu.slug == slug))
    return result.scalar_one_or_none() is not None


async def _load_course_with_items(session: AsyncSession, course_id: uuid.UUID) -> Course:
    result = await session.execute(
        select(Course)
        .execution_options(populate_existing=True)
        .options(selectinload(Course.items).selectinload(CourseItem.media_item))
        .where(Course.id == course_id)
    )
    course = result.scalar_one()
    return course


async def _load_course_item_with_media(session: AsyncSession, course_item_id: uuid.UUID) -> CourseItem:
    result = await session.execute(
        select(CourseItem)
        .execution_options(populate_existing=True)
        .options(selectinload(CourseItem.media_item))
        .where(CourseItem.id == course_item_id)
    )
    return result.scalar_one()


async def _load_menu_with_children(session: AsyncSession, menu_id: uuid.UUID) -> Menu:
    result = await session.execute(
        select(Menu)
        .execution_options(populate_existing=True)
        .options(selectinload(Menu.courses).selectinload(Course.items).selectinload(CourseItem.media_item))
        .where(Menu.id == menu_id)
    )
    return result.scalar_one()
