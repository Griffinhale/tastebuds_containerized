"""Tag CRUD and assignment services."""

from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media import MediaItem
from app.models.tagging import MediaItemTag, Tag
from app.schema.tag import TagCreate


async def list_tags(session: AsyncSession, owner_id: uuid.UUID) -> list[Tag]:
    """List user and shared tags sorted by name."""
    stmt = select(Tag).where(or_(Tag.owner_id == owner_id, Tag.owner_id.is_(None))).order_by(Tag.name.asc())
    result = await session.execute(stmt)
    return result.scalars().all()


async def list_media_tags(session: AsyncSession, owner_id: uuid.UUID, media_item_id: uuid.UUID) -> list[Tag]:
    """List tags assigned to a media item."""
    stmt = (
        select(Tag)
        .join(MediaItemTag, MediaItemTag.tag_id == Tag.id)
        .where(
            MediaItemTag.media_item_id == media_item_id,
            or_(Tag.owner_id == owner_id, Tag.owner_id.is_(None)),
        )
        .order_by(Tag.name.asc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def create_tag(session: AsyncSession, owner_id: uuid.UUID, payload: TagCreate) -> Tag:
    """Create a new tag scoped to an owner."""
    name = payload.name.strip()
    if not name:
        raise ValueError("Tag name cannot be blank")
    tag = Tag(owner_id=owner_id, name=name)
    session.add(tag)
    await session.commit()
    await session.refresh(tag)
    return tag


async def delete_tag(session: AsyncSession, owner_id: uuid.UUID, tag_id: uuid.UUID) -> None:
    """Delete a tag if it belongs to the owner."""
    tag = await session.get(Tag, tag_id)
    if not tag or tag.owner_id != owner_id:
        raise ValueError("Tag not found")
    await session.delete(tag)
    await session.commit()


async def add_tag_to_media(
    session: AsyncSession, owner_id: uuid.UUID, tag_id: uuid.UUID, media_item_id: uuid.UUID
) -> MediaItemTag:
    """Attach a tag to a media item, enforcing ownership rules."""
    tag = await session.get(Tag, tag_id)
    if not tag or (tag.owner_id not in (None, owner_id)):
        raise ValueError("Tag not available")

    media = await session.get(MediaItem, media_item_id)
    if not media:
        raise ValueError("Media item not found")

    stmt = select(MediaItemTag).where(
        MediaItemTag.media_item_id == media_item_id,
        MediaItemTag.tag_id == tag_id,
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    link = MediaItemTag(media_item_id=media_item_id, tag_id=tag_id)
    session.add(link)
    await session.commit()
    await session.refresh(link)
    return link


async def remove_tag_from_media(
    session: AsyncSession, owner_id: uuid.UUID, tag_id: uuid.UUID, media_item_id: uuid.UUID
) -> None:
    """Remove a tag from a media item if accessible."""
    tag = await session.get(Tag, tag_id)
    if not tag or (tag.owner_id not in (None, owner_id)):
        raise ValueError("Tag not available")
    stmt = select(MediaItemTag).where(
        MediaItemTag.media_item_id == media_item_id,
        MediaItemTag.tag_id == tag_id,
    )
    result = await session.execute(stmt)
    link = result.scalar_one_or_none()
    if not link:
        raise ValueError("Tag not assigned to media")
    await session.delete(link)
    await session.commit()
