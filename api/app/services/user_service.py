from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.models.user import User


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: str | uuid.UUID) -> User | None:
    try:
        user_uuid = uuid.UUID(str(user_id))
    except ValueError:
        return None
    result = await session.execute(select(User).where(User.id == user_uuid))
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, email: str, password: str, display_name: str | None = None) -> User:
    existing = await get_user_by_email(session, email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = User(email=email.lower(), hashed_password=get_password_hash(password), display_name=display_name)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate_user(session: AsyncSession, email: str, password: str) -> User:
    user = await get_user_by_email(session, email)
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return user
