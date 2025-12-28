"""Menu and course CRUD services with ordering invariants."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.media import MediaItem
from app.models.menu import Course, CourseItem, Menu, MenuItemPairing, MenuLineage, MenuShareToken
from app.models.search_preview import ExternalSearchPreview
from app.schema.menu import (
    CourseCreate,
    CourseItemCreate,
    CourseItemUpdate,
    CourseUpdate,
    MenuCreate,
    MenuForkCreate,
    MenuItemPairingCreate,
    MenuUpdate,
)
from app.services import media_service
from app.utils.slugify import menu_slug


def _menu_load_options():
    """Return common eager-loading options for menu reads."""
    return (
        selectinload(Menu.courses)
        .selectinload(Course.items)
        .selectinload(CourseItem.media_item)
        .selectinload(MediaItem.music),
        selectinload(Menu.pairings)
        .selectinload(MenuItemPairing.primary_item)
        .selectinload(CourseItem.media_item),
        selectinload(Menu.pairings)
        .selectinload(MenuItemPairing.paired_item)
        .selectinload(CourseItem.media_item),
    )


async def list_menus_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[Menu]:
    """List menus owned by a user with preloaded children."""
    result = await session.execute(
        select(Menu)
        .execution_options(populate_existing=True)
        .options(*_menu_load_options())
        .where(Menu.owner_id == user_id)
    )
    return result.scalars().all()


async def get_menu(session: AsyncSession, menu_id: uuid.UUID, *, owner_id: uuid.UUID | None = None) -> Menu:
    """Fetch a menu by ID, optionally scoping to an owner."""
    query = (
        select(Menu)
        .execution_options(populate_existing=True)
        .options(*_menu_load_options())
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
        .options(*_menu_load_options())
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


async def get_menu_for_fork(session: AsyncSession, menu_id: uuid.UUID, user_id: uuid.UUID) -> Menu:
    """Fetch a menu for forking if it is public or owned by the user."""
    result = await session.execute(
        select(Menu)
        .execution_options(populate_existing=True)
        .options(*_menu_load_options())
        .where(Menu.id == menu_id)
    )
    menu = result.scalar_one_or_none()
    if not menu:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu not found")
    if menu.owner_id != user_id and not menu.is_public:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu not found")
    return menu


async def fork_menu(
    session: AsyncSession,
    source_menu: Menu,
    owner_id: uuid.UUID,
    payload: MenuForkCreate,
) -> Menu:
    """Fork a menu into a new draft menu with lineage tracking."""
    title = payload.title or f"{source_menu.title} (Fork)"
    description = payload.description if payload.description is not None else source_menu.description
    is_public = payload.is_public if payload.is_public is not None else False
    slug = await _generate_unique_slug(session, title)

    menu = Menu(
        owner_id=owner_id,
        title=title,
        description=description,
        is_public=is_public,
        slug=slug,
    )
    session.add(menu)
    await session.flush()

    item_map: dict[uuid.UUID, uuid.UUID] = {}
    for course in source_menu.courses:
        new_course = Course(
            menu_id=menu.id,
            title=course.title,
            description=course.description,
            intent=course.intent,
            position=course.position,
        )
        session.add(new_course)
        await session.flush()
        for item in course.items:
            new_item = CourseItem(
                course_id=new_course.id,
                media_item_id=item.media_item_id,
                notes=item.notes,
                position=item.position,
            )
            session.add(new_item)
            await session.flush()
            item_map[item.id] = new_item.id

    for pairing in source_menu.pairings:
        primary_id = item_map.get(pairing.primary_course_item_id)
        paired_id = item_map.get(pairing.paired_course_item_id)
        if not primary_id or not paired_id:
            continue
        session.add(
            MenuItemPairing(
                menu_id=menu.id,
                primary_course_item_id=primary_id,
                paired_course_item_id=paired_id,
                relationship=pairing.relationship,
                note=pairing.note,
            )
        )

    session.add(
        MenuLineage(
            source_menu_id=source_menu.id,
            forked_menu_id=menu.id,
            created_by=owner_id,
            note=payload.note,
        )
    )
    await session.commit()
    return await _load_menu_with_children(session, menu.id)


async def list_pairings(
    session: AsyncSession,
    menu_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> list[MenuItemPairing]:
    """List narrative pairings for a menu."""
    result = await session.execute(
        select(MenuItemPairing)
        .join(Menu)
        .options(
            selectinload(MenuItemPairing.primary_item).selectinload(CourseItem.media_item),
            selectinload(MenuItemPairing.paired_item).selectinload(CourseItem.media_item),
        )
        .where(Menu.id == menu_id, Menu.owner_id == owner_id)
        .order_by(MenuItemPairing.created_at)
    )
    return result.scalars().all()


async def create_pairing(
    session: AsyncSession,
    menu: Menu,
    payload: MenuItemPairingCreate,
) -> MenuItemPairing:
    """Create a pairing between two course items in the same menu."""
    if payload.primary_course_item_id == payload.paired_course_item_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pairing must reference two items.")

    result = await session.execute(
        select(CourseItem)
        .join(Course)
        .where(
            CourseItem.id.in_([payload.primary_course_item_id, payload.paired_course_item_id]),
            Course.menu_id == menu.id,
        )
    )
    items = result.scalars().all()
    if len(items) != 2:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course item not found in menu")

    existing = await session.execute(
        select(MenuItemPairing).where(
            MenuItemPairing.menu_id == menu.id,
            MenuItemPairing.primary_course_item_id == payload.primary_course_item_id,
            MenuItemPairing.paired_course_item_id == payload.paired_course_item_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pairing already exists")

    pairing = MenuItemPairing(
        menu_id=menu.id,
        primary_course_item_id=payload.primary_course_item_id,
        paired_course_item_id=payload.paired_course_item_id,
        relationship=payload.relationship,
        note=payload.note,
    )
    session.add(pairing)
    await session.commit()
    return await _load_pairing_with_items(session, pairing.id)


async def get_pairing(
    session: AsyncSession,
    pairing_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> MenuItemPairing:
    """Fetch a pairing scoped to the menu owner."""
    result = await session.execute(
        select(MenuItemPairing)
        .join(Menu)
        .where(MenuItemPairing.id == pairing_id, Menu.owner_id == owner_id)
    )
    pairing = result.scalar_one_or_none()
    if not pairing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pairing not found")
    return pairing


async def delete_pairing(session: AsyncSession, pairing: MenuItemPairing) -> None:
    """Delete a pairing."""
    await session.delete(pairing)
    await session.commit()


async def list_share_tokens(
    session: AsyncSession,
    menu_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> list[MenuShareToken]:
    """List draft share tokens for a menu."""
    result = await session.execute(
        select(MenuShareToken)
        .join(Menu)
        .where(MenuShareToken.menu_id == menu_id, Menu.owner_id == owner_id)
        .order_by(MenuShareToken.created_at.desc())
    )
    return result.scalars().all()


async def create_share_token(
    session: AsyncSession,
    menu: Menu,
    *,
    created_by: uuid.UUID,
    expires_at: datetime | None = None,
) -> MenuShareToken:
    """Create a draft share token for a menu."""
    token = await _generate_share_token(session)
    ttl_days = getattr(settings, "draft_share_token_ttl_days", 7)
    default_expires = datetime.utcnow() + timedelta(days=ttl_days) if ttl_days > 0 else None
    share_token = MenuShareToken(
        menu_id=menu.id,
        created_by=created_by,
        token=token,
        expires_at=expires_at or default_expires,
    )
    session.add(share_token)
    await session.commit()
    await session.refresh(share_token)
    return share_token


async def revoke_share_token(
    session: AsyncSession,
    token_id: uuid.UUID,
    owner_id: uuid.UUID,
    *,
    menu_id: uuid.UUID | None = None,
) -> MenuShareToken:
    """Revoke a share token owned by the current user."""
    query = select(MenuShareToken).join(Menu).where(
        MenuShareToken.id == token_id, Menu.owner_id == owner_id
    )
    if menu_id:
        query = query.where(MenuShareToken.menu_id == menu_id)
    result = await session.execute(query)
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share token not found")
    if token.revoked_at is None:
        token.revoked_at = datetime.utcnow()
        await session.commit()
        await session.refresh(token)
    return token


async def get_menu_by_share_token(
    session: AsyncSession, token: str
) -> tuple[Menu, MenuShareToken]:
    """Resolve a menu from a draft share token."""
    result = await session.execute(
        select(MenuShareToken).where(MenuShareToken.token == token)
    )
    share_token = result.scalar_one_or_none()
    if not share_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found")
    now = datetime.utcnow()
    if share_token.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found")
    if share_token.expires_at and share_token.expires_at < now:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link expired")

    share_token.last_accessed_at = now
    share_token.access_count = (share_token.access_count or 0) + 1
    await session.commit()

    menu = await _load_menu_with_children(session, share_token.menu_id)
    return menu, share_token


async def get_menu_lineage_summary(
    session: AsyncSession,
    menu_id: uuid.UUID,
    *,
    include_private: bool,
) -> tuple[Menu | None, str | None, list[Menu]]:
    """Return lineage menus and attribution note."""
    result = await session.execute(
        select(MenuLineage).where(MenuLineage.forked_menu_id == menu_id)
    )
    source_link = result.scalar_one_or_none()
    source_menu = None
    source_note = None
    if source_link:
        source_menu = await session.get(Menu, source_link.source_menu_id)
        if source_menu and (include_private or source_menu.is_public):
            source_note = source_link.note
        else:
            source_menu = None

    forks_query = (
        select(Menu)
        .join(MenuLineage, MenuLineage.forked_menu_id == Menu.id)
        .where(MenuLineage.source_menu_id == menu_id)
        .order_by(Menu.created_at.desc())
    )
    if not include_private:
        forks_query = forks_query.where(Menu.is_public.is_(True))
    forks = (await session.execute(forks_query)).scalars().all()
    return source_menu, source_note, forks


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


async def _generate_share_token(session: AsyncSession) -> str:
    """Generate a unique share token."""
    while True:
        token = secrets.token_urlsafe(24)
        result = await session.execute(select(MenuShareToken).where(MenuShareToken.token == token))
        if result.scalar_one_or_none() is None:
            return token


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


async def _load_pairing_with_items(session: AsyncSession, pairing_id: uuid.UUID) -> MenuItemPairing:
    """Fetch a pairing with course items and media preloaded."""
    result = await session.execute(
        select(MenuItemPairing)
        .execution_options(populate_existing=True)
        .options(
            selectinload(MenuItemPairing.primary_item).selectinload(CourseItem.media_item),
            selectinload(MenuItemPairing.paired_item).selectinload(CourseItem.media_item),
        )
        .where(MenuItemPairing.id == pairing_id)
    )
    return result.scalar_one()


async def _load_menu_with_children(session: AsyncSession, menu_id: uuid.UUID) -> Menu:
    """Fetch a menu with courses and items preloaded."""
    result = await session.execute(
        select(Menu)
        .execution_options(populate_existing=True)
        .options(*_menu_load_options())
        .where(Menu.id == menu_id)
    )
    return result.scalar_one()
