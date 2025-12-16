from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.media import MediaSource
from app.models.menu import Course, Menu
from app.scripts import seed as seed_script


@pytest.mark.asyncio
async def test_seed_populates_demo_menu(session):
    await seed_script.seed(session=session)

    result = await session.execute(
        select(Menu).options(selectinload(Menu.courses).selectinload(Course.items))
    )
    menus = result.scalars().all()
    assert len(menus) == 1
    menu = menus[0]
    assert menu.title == seed_script.MENU_TITLE
    assert menu.slug == seed_script.MENU_SLUG
    assert [course.position for course in menu.courses] == [1, 2, 3]
    assert [item.position for item in menu.courses[1].items] == [1, 2]

    source_stmt = select(MediaSource).where(
        MediaSource.source_name == "google_books",
        MediaSource.external_id == "demo-book-001",
    )
    source = (await session.execute(source_stmt)).scalar_one()
    assert source.raw_payload["id"] == "demo-book-001"


@pytest.mark.asyncio
async def test_seed_is_idempotent(session):
    await seed_script.seed(session=session)
    await seed_script.seed(session=session)

    menus = (await session.execute(select(Menu))).scalars().all()
    assert len(menus) == 1

    sources = (await session.execute(select(MediaSource))).scalars().all()
    assert len(sources) == len(seed_script.SEED_MEDIA)
