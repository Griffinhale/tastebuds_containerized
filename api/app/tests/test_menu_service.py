"""Menu service tests for slugging and update invariants."""

from __future__ import annotations

import pytest
from fastapi import HTTPException, status

from app.models.media import MediaItem, MediaType
from app.models.user import User
from app.schema.menu import CourseCreate, CourseItemCreate, CourseItemUpdate, CourseUpdate, MenuCreate, MenuUpdate
from app.services import menu_service


@pytest.mark.asyncio
async def test_menu_slug_uniqueness(session):
    user = User(email="slug@test", hashed_password="x")
    session.add(user)
    await session.flush()

    payload = MenuCreate(title="Neo Noir Night", description="test", is_public=True)
    first = await menu_service.create_menu(session, user.id, payload)
    second = await menu_service.create_menu(session, user.id, payload)

    assert first.slug == "neo-noir-night"
    assert second.slug == "neo-noir-night-2"


@pytest.mark.asyncio
async def test_menu_slug_stable_on_update(session):
    user = User(email="slug-stable@test", hashed_password="x")
    session.add(user)
    await session.flush()

    menu = await menu_service.create_menu(
        session,
        user.id,
        MenuCreate(title="Creative Sparks", description=None, is_public=False),
    )

    original_slug = menu.slug
    updated = await menu_service.update_menu(
        session,
        menu,
        MenuUpdate(title="Creative Sparks Remix", description="new desc", is_public=True),
    )

    assert updated.slug == original_slug


@pytest.mark.asyncio
async def test_course_intent_updates(session):
    user = User(email="course-intent@test", hashed_password="x")
    session.add(user)
    await session.flush()

    menu = await menu_service.create_menu(
        session,
        user.id,
        MenuCreate(title="Narrative Menu", description=None, is_public=False),
    )

    course = await menu_service.add_course(
        session,
        menu,
        CourseCreate(title="Course One", description="Start here", intent="Set the mood", position=1),
    )

    updated = await menu_service.update_course(
        session,
        course,
        CourseUpdate(intent="Raise the stakes", description="Updated"),
    )

    assert updated.intent == "Raise the stakes"
    assert updated.description == "Updated"


@pytest.mark.asyncio
async def test_course_update_rejects_stale_timestamp(session):
    user = User(email="course-stale@test", hashed_password="x")
    session.add(user)
    await session.flush()

    menu = await menu_service.create_menu(
        session,
        user.id,
        MenuCreate(title="Timewarp Menu", description=None, is_public=False),
    )

    course = await menu_service.add_course(
        session,
        menu,
        CourseCreate(title="Course One", description=None, intent=None, position=1),
    )

    stale_updated_at = course.updated_at
    updated = await menu_service.update_course(
        session,
        course,
        CourseUpdate(title="Fresh Title", expected_updated_at=stale_updated_at),
    )

    with pytest.raises(HTTPException) as exc:
        await menu_service.update_course(
            session,
            updated,
            CourseUpdate(title="Stale Attempt", expected_updated_at=stale_updated_at),
        )

    assert exc.value.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_course_item_update_rejects_stale_timestamp(session):
    user = User(email="item-stale@test", hashed_password="x")
    session.add(user)
    await session.flush()

    menu = await menu_service.create_menu(
        session,
        user.id,
        MenuCreate(title="Item Timewarp", description=None, is_public=False),
    )

    course = await menu_service.add_course(
        session,
        menu,
        CourseCreate(title="Course One", description=None, intent=None, position=1),
    )

    media = MediaItem(media_type=MediaType.BOOK, title="Stale Book")
    session.add(media)
    await session.flush()

    course_item = await menu_service.add_course_item(
        session,
        course,
        CourseItemCreate(media_item_id=media.id, position=1, notes="First"),
    )

    stale_updated_at = course_item.updated_at
    updated = await menu_service.update_course_item(
        session,
        course_item,
        CourseItemUpdate(notes="Updated", expected_updated_at=stale_updated_at),
    )

    with pytest.raises(HTTPException) as exc:
        await menu_service.update_course_item(
            session,
            updated,
            CourseItemUpdate(notes="Stale update", expected_updated_at=stale_updated_at),
        )

    assert exc.value.status_code == status.HTTP_409_CONFLICT
