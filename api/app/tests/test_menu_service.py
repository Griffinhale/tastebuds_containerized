from __future__ import annotations

import pytest

from app.models.user import User
from app.schema.menu import MenuCreate, MenuUpdate
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
