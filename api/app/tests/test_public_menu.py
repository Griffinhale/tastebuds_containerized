from __future__ import annotations

import pytest

from app.models.menu import Menu
from app.models.user import User
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
