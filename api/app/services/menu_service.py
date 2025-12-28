"""Menu and course CRUD services with ordering invariants."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.media import MediaItem
from app.models.menu import Course, CourseItem, Menu
from app.models.search_preview import ExternalSearchPreview
from app.schema.menu import CourseCreate, CourseItemCreate, CourseItemUpdate, CourseUpdate, MenuCreate, MenuUpdate
from app.services import media_service
from app.utils.slugify import menu_slug


async def list_menus_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[Menu]:
    """List menus owned by a user with preloaded children."""
    result = await session.execute(
        select(Menu)
        .execution_options(populate_existing=True)
        .options(selectinload(Menu.courses).selectinload(Course.items).selectinload(CourseItem.media_item))
        .where(Menu.owner_id == user_id)
    )
    return result.scalars().all()


async def get_menu(session: AsyncSession, menu_id: uuid.UUID, *, owner_id: uuid.UUID | None = None) -> Menu:
    """Fetch a menu by ID, optionally scoping to an owner."""
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
    """Fetch a public menu by slug."""
    result = await session.execute(
        select(Menu)
        .execution_options(populate_existing=True)
        .options(selectinload(Menu.courses).selectinload(Course.items).selectinload(CourseItem.media_item))
        .where(Menu.slug == slug, Menu.is_public.is_(True))
    )
    return result.scalar_one_or_none()


async def create_menu(session: AsyncSession, owner_id: uuid.UUID, payload: MenuCreate) -> Menu:
    """Create a menu and any nested courses/items."""
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
    """Update mutable menu attributes."""
    if payload.title:
        menu.title = payload.title
    if payload.description is not None:
        menu.description = payload.description
    if payload.is_public is not None:
        menu.is_public = payload.is_public
    await session.commit()
    return await _load_menu_with_children(session, menu.id)


async def delete_menu(session: AsyncSession, menu: Menu) -> None:
    """Delete a menu and its children."""
    await session.delete(menu)
    await session.commit()


async def add_course(session: AsyncSession, menu: Menu, payload: CourseCreate) -> Course:
    """Append a course to an existing menu."""
    course = await _create_course(session, menu, payload)
    await session.commit()
    return await _load_course_with_items(session, course.id)


async def update_course(session: AsyncSession, course: Course, payload: CourseUpdate) -> Course:
    """Update mutable course attributes."""
    _ensure_fresh_update(course.updated_at, payload.expected_updated_at, label="Course")
    fields = payload.model_fields_set
    if "title" in fields and payload.title is not None:
        course.title = payload.title
    if "description" in fields:
        course.description = payload.description
    if "intent" in fields:
        course.intent = payload.intent
    await session.commit()
    return await _load_course_with_items(session, course.id)


async def get_course(session: AsyncSession, course_id: uuid.UUID, owner_id: uuid.UUID) -> Course:
    """Fetch a course scoped to an owner."""
    query = select(Course).join(Menu).where(Course.id == course_id, Menu.owner_id == owner_id)
    result = await session.execute(query)
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return course


async def add_course_item(session: AsyncSession, course: Course, payload: CourseItemCreate) -> CourseItem:
    """Attach a media item to a course."""
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


async def update_course_item(
    session: AsyncSession, course_item: CourseItem, payload: CourseItemUpdate
) -> CourseItem:
    """Update mutable course item attributes."""
    _ensure_fresh_update(course_item.updated_at, payload.expected_updated_at, label="Course item")
    if "notes" in payload.model_fields_set:
        course_item.notes = payload.notes
    await session.commit()
    return await _load_course_item_with_media(session, course_item.id)


async def delete_course(session: AsyncSession, course: Course) -> None:
    """Delete a course and its items."""
    await session.delete(course)
    await session.commit()


async def get_course_item(session: AsyncSession, item_id: uuid.UUID, owner_id: uuid.UUID) -> CourseItem:
    """Fetch a course item scoped to an owner."""
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
    """Delete a course item."""
    await session.delete(course_item)
    await session.commit()


async def reorder_course_items(
    session: AsyncSession,
    course: Course,
    item_ids: list[uuid.UUID],
) -> Course:
    """Reorder course items while preserving uniqueness constraints.

    Implementation notes:
    - The two-phase update avoids unique constraint collisions on position.
    """
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
    # Bump positions out of the way before assigning final order.
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
        .values(
            position=case(*whens, else_=CourseItem.position),
            updated_at=func.now(),
        )
    )
    await session.commit()
    return await _load_course_with_items(session, course.id)


async def _create_course(session: AsyncSession, menu: Menu, payload: CourseCreate) -> Course:
    """Create a course and its items without committing."""
    course = Course(
        menu_id=menu.id,
        title=payload.title,
        description=payload.description,
        intent=payload.intent,
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
    """Resolve media by ID or ingest from a preview if present."""
    result = await session.execute(select(MediaItem).where(MediaItem.id == media_item_id))
    media = result.scalar_one_or_none()
    if not media:
        preview = await session.get(ExternalSearchPreview, media_item_id)
        if preview:
            media = await media_service.ingest_from_source(
                session, source=preview.source_name, identifier=preview.external_id
            )
            await session.delete(preview)
            await session.commit()
            return media
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found")
    return media


async def _generate_unique_slug(session: AsyncSession, title: str) -> str:
    """Generate a menu slug that does not collide with existing menus."""
    base = menu_slug(title) or "menu"
    slug = base
    counter = 1
    while await _slug_exists(session, slug):
        counter += 1
        slug = f"{base}-{counter}"
    return slug


async def _slug_exists(session: AsyncSession, slug: str) -> bool:
    """Return True if a menu slug already exists."""
    result = await session.execute(select(Menu).where(Menu.slug == slug))
    return result.scalar_one_or_none() is not None


def _ensure_fresh_update(
    current: datetime | None,
    expected: datetime | None,
    *,
    label: str,
) -> None:
    """Guard against stale updates by comparing timestamps."""
    if expected is None or current is None:
        return

    current_utc = _to_utc(current)
    expected_utc = _to_utc(expected)
    if current_utc != expected_utc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": f"{label} was updated by another session.",
                "current_updated_at": current_utc.isoformat(),
            },
        )


def _to_utc(value: datetime) -> datetime:
    """Normalize timestamps to UTC for safe comparisons."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def _load_course_with_items(session: AsyncSession, course_id: uuid.UUID) -> Course:
    """Fetch a course with items and media preloaded."""
    result = await session.execute(
        select(Course)
        .execution_options(populate_existing=True)
        .options(selectinload(Course.items).selectinload(CourseItem.media_item))
        .where(Course.id == course_id)
    )
    course = result.scalar_one()
    return course


async def _load_course_item_with_media(session: AsyncSession, course_item_id: uuid.UUID) -> CourseItem:
    """Fetch a course item with its media preloaded."""
    result = await session.execute(
        select(CourseItem)
        .execution_options(populate_existing=True)
        .options(selectinload(CourseItem.media_item))
        .where(CourseItem.id == course_item_id)
    )
    return result.scalar_one()


async def _load_menu_with_children(session: AsyncSession, menu_id: uuid.UUID) -> Menu:
    """Fetch a menu with courses and items preloaded."""
    result = await session.execute(
        select(Menu)
        .execution_options(populate_existing=True)
        .options(selectinload(Menu.courses).selectinload(Course.items).selectinload(CourseItem.media_item))
        .where(Menu.id == menu_id)
    )
    return result.scalar_one()
