"""Tag service tests for lifecycle and access control."""

from __future__ import annotations

import pytest

from app.models.media import MediaItem, MediaType
from app.models.user import User
from app.schema.tag import TagCreate
from app.services import tag_service


@pytest.mark.asyncio
async def test_tag_lifecycle(session):
    user = User(email="tag@test", hashed_password="x")
    media = MediaItem(media_type=MediaType.BOOK, title="Tagged Book")
    session.add_all([user, media])
    await session.commit()

    created = await tag_service.create_tag(session, user.id, TagCreate(name="Noir"))
    listed = await tag_service.list_tags(session, user.id)
    assert any(tag.id == created.id for tag in listed)

    await tag_service.add_tag_to_media(session, user.id, created.id, media.id)
    media_tags = await tag_service.list_media_tags(session, user.id, media.id)
    assert len(media_tags) == 1
    assert media_tags[0].name == "Noir"

    await tag_service.remove_tag_from_media(session, user.id, created.id, media.id)
    assert not await tag_service.list_media_tags(session, user.id, media.id)

    await tag_service.delete_tag(session, user.id, created.id)
    assert not any(tag.id == created.id for tag in await tag_service.list_tags(session, user.id))


@pytest.mark.asyncio
async def test_tag_access_control(session):
    owner = User(email="tag-owner@test", hashed_password="x")
    other = User(email="tag-other@test", hashed_password="x")
    media = MediaItem(media_type=MediaType.MOVIE, title="Movie")
    session.add_all([owner, other, media])
    await session.commit()

    tag = await tag_service.create_tag(session, owner.id, TagCreate(name="Owner Only"))

    with pytest.raises(ValueError):
        await tag_service.add_tag_to_media(session, other.id, tag.id, media.id)
