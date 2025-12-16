from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db.session import async_session
from app.models.media import MediaItem, MediaType, UserItemStatus
from app.schema.media import UserItemStateUpdate
from app.schema.menu import CourseCreate, CourseItemCreate, MenuCreate
from app.schema.tag import TagCreate
from app.services import menu_service, tag_service, user_service, user_state_service


async def seed() -> None:
    async with async_session() as session:
        user = await user_service.get_user_by_email(session, "demo@tastebuds.local")
        if not user:
            user = await user_service.create_user(
                session, email="demo@tastebuds.local", password="changeme123", display_name="Demo User"
            )

        media_items = await session.execute(select(MediaItem))
        existing = {item.title: item for item in media_items.scalars()}
        if not existing:
            book = MediaItem(media_type=MediaType.BOOK, title="The Taste of Innovation", description="Design thinking in media")
            movie = MediaItem(media_type=MediaType.MOVIE, title="Cinematic Journeys", description="Anthology of visionary films")
            game = MediaItem(media_type=MediaType.GAME, title="Quest for Flavor", description="Indie narrative adventure")
            track = MediaItem(media_type=MediaType.MUSIC, title="Soundtrack of Curiosity", description="An ambient score")
            session.add_all([book, movie, game, track])
            await session.commit()
            for item in (book, movie, game, track):
                await session.refresh(item)
            existing = {item.title: item for item in (book, movie, game, track)}

        menu_payload = MenuCreate(
            title="Creative Sparks Menu",
            description="A starter, main, and dessert course of media inspiration",
            is_public=True,
            courses=[
                CourseCreate(
                    title="Appetizer",
                    description="Warm up the senses",
                    position=1,
                    items=[
                        CourseItemCreate(media_item_id=existing["The Taste of Innovation"].id, notes="Skim chapters 1-3", position=1)
                    ],
                ),
                CourseCreate(
                    title="Main",
                    description="Immerse in narrative",
                    position=2,
                    items=[
                        CourseItemCreate(media_item_id=existing["Cinematic Journeys"].id, notes="Watch with friends", position=1),
                        CourseItemCreate(media_item_id=existing["Quest for Flavor"].id, notes="Co-op mode recommended", position=2),
                    ],
                ),
                CourseCreate(
                    title="Dessert",
                    description="Reflect with music",
                    position=3,
                    items=[
                        CourseItemCreate(media_item_id=existing["Soundtrack of Curiosity"].id, notes="Headphones on", position=1)
                    ],
                ),
            ],
        )

        menus = await menu_service.list_menus_for_user(session, user.id)
        if not menus:
            await menu_service.create_menu(session, user.id, menu_payload)

        tag_names = ("Inspiration", "Cinematic", "Reflective")
        existing_tags = {
            tag.name: tag
            for tag in await tag_service.list_tags(session, user.id)
            if tag.owner_id == user.id
        }
        for name in tag_names:
            if name not in existing_tags:
                existing_tags[name] = await tag_service.create_tag(session, user.id, TagCreate(name=name))

        await tag_service.add_tag_to_media(
            session, user.id, existing_tags["Inspiration"].id, existing["The Taste of Innovation"].id
        )
        await tag_service.add_tag_to_media(
            session, user.id, existing_tags["Cinematic"].id, existing["Cinematic Journeys"].id
        )

        await user_state_service.upsert_state(
            session,
            user.id,
            existing["The Taste of Innovation"].id,
            UserItemStateUpdate(status=UserItemStatus.CONSUMED, rating=8, favorite=True),
        )
        await user_state_service.upsert_state(
            session,
            user.id,
            existing["Quest for Flavor"].id,
            UserItemStateUpdate(status=UserItemStatus.WANT, notes="Finish after movie night"),
        )

        print("Seed complete")


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
