from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.auth import RefreshToken


def _hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _generate_token_value() -> str:
    # 64 bytes -> 86 char urlsafe string; plenty of entropy
    return secrets.token_urlsafe(64)


def _current_time() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_timezone(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt
    return dt.replace(tzinfo=timezone.utc)


def _build_refresh_token(user_id: uuid.UUID) -> tuple[str, RefreshToken]:
    token_value = _generate_token_value()
    token_hash = _hash_token(token_value)
    expires_at = _current_time() + timedelta(minutes=settings.refresh_token_expires_minutes)
    token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    return token_value, token


async def _get_token_by_value(session: AsyncSession, token_value: str) -> RefreshToken | None:
    token_hash = _hash_token(token_value)
    result = await session.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    return result.scalar_one_or_none()


async def _revoke_descendant_tokens(
    session: AsyncSession, token_id: uuid.UUID, *, reason: str = "reused_token"
) -> None:
    next_id = token_id
    while next_id:
        descendant = await session.get(RefreshToken, next_id)
        if not descendant:
            break
        if not descendant.revoked_at:
            descendant.revoked_at = _current_time()
            descendant.revoked_reason = reason
        next_id = descendant.replaced_by_token_id


async def issue_refresh_token(session: AsyncSession, user_id: uuid.UUID) -> str:
    token_value, token = _build_refresh_token(user_id)
    session.add(token)
    await session.commit()
    return token_value


async def rotate_refresh_token(session: AsyncSession, token_value: str) -> tuple[str, uuid.UUID] | None:
    token = await _get_token_by_value(session, token_value)
    if not token:
        return None

    now = _current_time()
    if token.revoked_at:
        if token.revoked_reason == "rotated" and token.replaced_by_token_id:
            await _revoke_descendant_tokens(session, token.replaced_by_token_id)
            await session.commit()
        return None

    token.expires_at = _ensure_timezone(token.expires_at)
    expires_at = token.expires_at
    if expires_at <= now:
        token.revoked_at = now
        token.revoked_reason = "expired"
        await session.commit()
        return None

    new_value, new_token = _build_refresh_token(token.user_id)
    session.add(new_token)
    await session.flush()

    token.revoked_at = now
    token.revoked_reason = "rotated"
    token.replaced_by_token_id = new_token.id

    await session.commit()
    return new_value, token.user_id


async def revoke_refresh_token(session: AsyncSession, token_value: str, *, reason: str = "revoked") -> None:
    token = await _get_token_by_value(session, token_value)
    if not token or token.revoked_at:
        return
    token.revoked_at = _current_time()
    token.revoked_reason = reason
    await session.commit()
