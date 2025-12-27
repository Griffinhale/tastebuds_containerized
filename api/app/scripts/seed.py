"""Seed script for demo data in local/dev environments."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import async_session
from app.models.media import (
    BookItem,
    GameItem,
    MediaItem,
    MediaSource,
    MediaType,
    MovieItem,
    MusicItem,
    UserItemStatus,
)
from app.models.menu import Menu
from app.samples import load_ingestion_sample
from app.schema.media import UserItemStateUpdate
from app.schema.menu import CourseCreate, CourseItemCreate, MenuCreate
from app.schema.tag import TagCreate
from app.services import menu_service, tag_service, user_service, user_state_service
from app.utils.slugify import menu_slug

DEMO_EMAIL = "demo@tastebuds.local"
DEMO_PASSWORD = "changeme123"
DEMO_DISPLAY_NAME = "Demo User"
MENU_TITLE = "Creative Sparks Menu"
MENU_SLUG = menu_slug(MENU_TITLE)


@dataclass(frozen=True)
class SeedMediaDefinition:
    """Structured definition for seed media items and source payloads."""
    key: str
    media_type: MediaType
    title: str
    description: str
    release_date: date | None
    metadata: Mapping[str, Any]
    extension: Mapping[str, Any]
    source_name: str
    external_id: str
    canonical_url: str | None
    raw_payload: Mapping[str, Any]


SEED_MEDIA: tuple[SeedMediaDefinition, ...] = (
    SeedMediaDefinition(
        key="book",
        media_type=MediaType.BOOK,
        title="The Taste of Innovation",
        description="Design thinking in media",
        release_date=date(2023, 1, 17),
        metadata={
            "categories": ["Design", "Storytelling"],
            "maturity_rating": "NOT_MATURE",
        },
        extension={
            "authors": ["Alexis Rowe"],
            "page_count": 312,
            "publisher": "Archive Press",
            "language": "en",
            "isbn_13": "9780000000012",
        },
        source_name="google_books",
        external_id="demo-book-001",
        canonical_url="https://books.google.com/demo-book-001",
        raw_payload=load_ingestion_sample("google_books_volume"),
    ),
    SeedMediaDefinition(
        key="movie",
        media_type=MediaType.MOVIE,
        title="Cinematic Journeys",
        description="Anthology of visionary films",
        release_date=date(2021, 8, 5),
        metadata={
            "genres": ["Drama", "Adventure"],
            "languages": [
                {"english_name": "English", "iso_639_1": "en", "name": "English"},
            ],
            "status": "Released",
        },
        extension={
            "runtime_minutes": 138,
            "directors": ["T. Laird"],
            "tmdb_type": "movie",
        },
        source_name="tmdb",
        external_id="603",
        canonical_url="https://www.themoviedb.org/movie/603",
        raw_payload=load_ingestion_sample("tmdb_movie"),
    ),
    SeedMediaDefinition(
        key="game",
        media_type=MediaType.GAME,
        title="Quest for Flavor",
        description="Indie narrative adventure",
        release_date=date(2020, 5, 9),
        metadata={
            "genres": ["Adventure"],
            "platforms": ["pc", "switch"],
        },
        extension={
            "platforms": ["PC", "Switch"],
            "developers": ["Calico Works"],
            "publishers": ["Calico Works"],
            "genres": ["Adventure"],
        },
        source_name="igdb",
        external_id="demo-game-7346",
        canonical_url="https://www.igdb.com/games/demo-game-7346",
        raw_payload=load_ingestion_sample("igdb_game"),
    ),
    SeedMediaDefinition(
        key="music",
        media_type=MediaType.MUSIC,
        title="Soundtrack of Curiosity",
        description="An ambient score",
        release_date=date(2022, 3, 14),
        metadata={
            "listeners": "12000",
            "playcount": "48000",
            "tags": ["ambient", "focus"],
        },
        extension={
            "artist_name": "Nia Holloway",
            "album_name": "Resonant Paths",
            "track_number": 3,
            "duration_ms": 226000,
        },
        source_name="lastfm",
        external_id="demo-track-curiosity",
        canonical_url="https://www.last.fm/music/Nia+Holloway/_/Soundtrack+of+Curiosity",
        raw_payload=load_ingestion_sample("lastfm_track"),
    ),
)


async def seed(session: AsyncSession | None = None) -> None:
    """Seed demo data into the database."""
    if session is None:
        async with async_session() as managed_session:
            await _seed_session(managed_session)
    else:
        await _seed_session(session)


async def _seed_session(session: AsyncSession) -> None:
    """Populate a session with demo users, menus, and media."""
    user = await user_service.get_user_by_email(session, DEMO_EMAIL)
    if not user:
        user = await user_service.create_user(
            session,
            email=DEMO_EMAIL,
            password=DEMO_PASSWORD,
            display_name=DEMO_DISPLAY_NAME,
        )

    media_items = await _ensure_media_items(session)
    menu = await _ensure_menu(session, user.id, media_items)
    await _ensure_tags(session, user.id, media_items)
    await _ensure_user_states(session, user.id, media_items)

    print(f"Seed complete - menu slug: {menu.slug}")


async def _ensure_media_items(session: AsyncSession) -> dict[str, MediaItem]:
    """Ensure seed media items exist and return them keyed by label."""
    items: dict[str, MediaItem] = {}
    for definition in SEED_MEDIA:
        items[definition.key] = await _get_or_create_media(session, definition)
    return items


async def _get_or_create_media(session: AsyncSession, definition: SeedMediaDefinition) -> MediaItem:
    """Create media + source records if they do not already exist."""
    stmt = (
        select(MediaSource)
        .options(selectinload(MediaSource.media_item))
        .where(
            MediaSource.source_name == definition.source_name,
            MediaSource.external_id == definition.external_id,
        )
    )
    result = await session.execute(stmt)
    source = result.scalar_one_or_none()
    if source:
        return source.media_item

    media = MediaItem(
        media_type=definition.media_type,
        title=definition.title,
        description=definition.description,
        release_date=definition.release_date,
        canonical_url=definition.canonical_url,
        metadata=definition.metadata,
    )
    session.add(media)
    await session.flush()
    _attach_extension(session, media.id, definition)
    session.add(
        MediaSource(
            media_item_id=media.id,
            source_name=definition.source_name,
            external_id=definition.external_id,
            canonical_url=definition.canonical_url,
            raw_payload=dict(definition.raw_payload),
        )
    )
    await session.commit()
    await session.refresh(media)
    return media


def _attach_extension(session: AsyncSession, media_item_id, definition: SeedMediaDefinition) -> None:
    """Attach the correct media extension row for the seed item."""
    data = dict(definition.extension)
    if definition.media_type == MediaType.BOOK:
        session.add(BookItem(media_item_id=media_item_id, **data))
    elif definition.media_type == MediaType.MOVIE:
        session.add(MovieItem(media_item_id=media_item_id, **data))
    elif definition.media_type == MediaType.GAME:
        session.add(GameItem(media_item_id=media_item_id, **data))
    elif definition.media_type == MediaType.TV:
        session.add(MovieItem(media_item_id=media_item_id, **data))
    elif definition.media_type == MediaType.MUSIC:
        session.add(MusicItem(media_item_id=media_item_id, **data))


async def _ensure_menu(session: AsyncSession, user_id, media_items: dict[str, MediaItem]) -> Menu:
    """Create the demo menu if it is missing."""
    stmt = select(Menu).where(Menu.owner_id == user_id, Menu.slug == MENU_SLUG)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    menu_payload = MenuCreate(
        title=MENU_TITLE,
        description="A starter, main, and dessert course of media inspiration",
        is_public=True,
        courses=[
            CourseCreate(
                title="Appetizer",
                description="Warm up the senses",
                position=1,
                items=[
                    CourseItemCreate(
                        media_item_id=media_items["book"].id,
                        notes="Skim chapters 1-3",
                        position=1,
                    )
                ],
            ),
            CourseCreate(
                title="Main",
                description="Immerse in narrative",
                position=2,
                items=[
                    CourseItemCreate(
                        media_item_id=media_items["movie"].id,
                        notes="Watch with friends",
                        position=1,
                    ),
                    CourseItemCreate(
                        media_item_id=media_items["game"].id,
                        notes="Co-op mode recommended",
                        position=2,
                    ),
                ],
            ),
            CourseCreate(
                title="Dessert",
                description="Reflect with music",
                position=3,
                items=[
                    CourseItemCreate(
                        media_item_id=media_items["music"].id,
                        notes="Headphones on",
                        position=1,
                    )
                ],
            ),
        ],
    )
    return await menu_service.create_menu(session, user_id, menu_payload)


async def _ensure_tags(session: AsyncSession, user_id, media_items: dict[str, MediaItem]) -> None:
    """Create demo tags and attach them to media items."""
    tag_names = ("Inspiration", "Cinematic", "Reflective")
    existing_tags = {tag.name: tag for tag in await tag_service.list_tags(session, user_id) if tag.owner_id == user_id}
    for name in tag_names:
        if name not in existing_tags:
            existing_tags[name] = await tag_service.create_tag(session, user_id, TagCreate(name=name))

    await tag_service.add_tag_to_media(session, user_id, existing_tags["Inspiration"].id, media_items["book"].id)
    await tag_service.add_tag_to_media(session, user_id, existing_tags["Cinematic"].id, media_items["movie"].id)


async def _ensure_user_states(session: AsyncSession, user_id, media_items: dict[str, MediaItem]) -> None:
    """Set up demo user state entries for selected items."""
    await user_state_service.upsert_state(
        session,
        user_id,
        media_items["book"].id,
        UserItemStateUpdate(status=UserItemStatus.CONSUMED, rating=8, favorite=True),
    )
    await user_state_service.upsert_state(
        session,
        user_id,
        media_items["game"].id,
        UserItemStateUpdate(status=UserItemStatus.WANT, notes="Finish after movie night"),
    )


def main() -> None:
    """CLI entrypoint for seeding demo data."""
    asyncio.run(seed())


if __name__ == "__main__":
    main()
