"""Tests for public menu access and ordering guarantees."""

from __future__ import annotations

import pytest

from app.models.media import MediaItem, MediaType
from app.models.menu import Menu
from app.models.user import User
from app.schema.menu import CourseCreate, CourseItemCreate, MenuCreate
from app.services import menu_service


@pytest.mark.asyncio
async def test_public_menu_lookup(session):
    user = User(email="public@test", hashed_password="x")
    session.add(user)
    await session.flush()

    menu = Menu(owner_id=user.id, title="Public Menu", description="", slug="public-menu", is_public=True)
    session.add(menu)
    await session.commit()

    found = await menu_service.get_menu_by_slug(session, "public-menu")
    assert found is not None
    assert found.slug == "public-menu"

    menu.is_public = False
    await session.commit()

    hidden = await menu_service.get_menu_by_slug(session, "public-menu")
    assert hidden is None


@pytest.mark.asyncio
async def test_public_menu_respects_ordering(session):
    user = User(email="ordering@test", hashed_password="x")
    session.add(user)

    book = MediaItem(media_type=MediaType.BOOK, title="A", description=None)
    movie = MediaItem(media_type=MediaType.MOVIE, title="B", description=None)
    session.add_all([book, movie])
    await session.commit()

    payload = MenuCreate(
        title="Ordering Proof",
        description=None,
        is_public=True,
        courses=[
            CourseCreate(
                title="Second",
                description=None,
                position=2,
                items=[
                    CourseItemCreate(media_item_id=movie.id, notes=None, position=2),
                    CourseItemCreate(media_item_id=book.id, notes=None, position=1),
                ],
            ),
            CourseCreate(
                title="First",
                description=None,
                position=1,
                items=[
                    CourseItemCreate(media_item_id=book.id, notes=None, position=1),
                ],
            ),
        ],
    )

    menu = await menu_service.create_menu(session, user.id, payload)
    found = await menu_service.get_menu_by_slug(session, menu.slug)
    assert [course.position for course in found.courses] == [1, 2]
    assert [item.position for item in found.courses[1].items] == [1, 2]


@pytest.mark.asyncio
async def test_public_menu_route_hides_owner_id(client, session):
    user = User(email="route@test", hashed_password="x")
    session.add(user)
    await session.flush()

    payload = MenuCreate(title="Public Route", is_public=True)
    menu = await menu_service.create_menu(session, user.id, payload)

    response = await client.get(f"/api/public/menus/{menu.slug}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["slug"] == menu.slug
    assert payload["is_public"] is True
    assert "owner_id" not in payload
