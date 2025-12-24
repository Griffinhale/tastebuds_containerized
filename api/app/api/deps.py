from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_token
from app.db.session import get_session
from app.models.user import User
from app.services import user_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/login", auto_error=False)


async def get_db() -> AsyncSession:
    async for session in get_session():
        yield session


async def get_current_user(
    session: AsyncSession = Depends(get_db),
    token: str | None = Depends(oauth2_scheme),
    access_token_cookie: str | None = Cookie(default=None, alias="access_token"),
) -> User:
    candidate = token or access_token_cookie
    if not candidate:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return await _resolve_user_from_token(session, candidate)


async def _resolve_user_from_token(session: AsyncSession, token: str) -> User:
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user_id = payload.get("sub")
    user = await user_service.get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_optional_current_user(
    session: AsyncSession = Depends(get_db),
    token: str | None = Depends(oauth2_scheme),
    access_token_cookie: str | None = Cookie(default=None, alias="access_token"),
) -> User | None:
    candidate = token or access_token_cookie
    if not candidate:
        return None
    return await _resolve_user_from_token(session, candidate)
