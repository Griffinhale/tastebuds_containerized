from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Body, Cookie, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.security import create_access_token
from app.schema.auth import SessionRead, TokenPair
from app.schema.user import UserCreate, UserLogin, UserRead
from app.models.user import User
from app.services import refresh_token_service, user_service

router = APIRouter()

ACCESS_COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    secure = settings.environment.lower() == "production"
    response.set_cookie(
        ACCESS_COOKIE_NAME,
        access_token,
        max_age=settings.access_token_expires_minutes * 60,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=settings.refresh_token_expires_minutes * 60,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    secure = settings.environment.lower() == "production"
    for name in (ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME):
        directives = ["Path=/", "HttpOnly", "SameSite=Lax"]
        if secure:
            directives.append("Secure")
        header_value = f"{name}=; {'; '.join(directives)}"
        response.raw_headers.append((b"set-cookie", header_value.encode("latin-1")))


def _normalize_timestamp(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _serialize_session(token, current_token_id: UUID | None) -> SessionRead:
    expires_at = _normalize_timestamp(token.expires_at)
    revoked_at = _normalize_timestamp(token.revoked_at)
    created_at = _normalize_timestamp(token.created_at)
    now = datetime.now(timezone.utc)
    is_active = revoked_at is None and expires_at and expires_at > now
    return SessionRead(
        id=token.id,
        created_at=created_at,
        expires_at=expires_at,
        revoked_at=revoked_at,
        revoked_reason=token.revoked_reason,
        replaced_by_token_id=token.replaced_by_token_id,
        is_active=is_active,
        is_current=current_token_id == token.id,
    )


async def _token_response(session: AsyncSession, user: UserRead) -> TokenPair:
    access = create_access_token(str(user.id))
    refresh = await refresh_token_service.issue_refresh_token(session, user.id)
    return TokenPair(access_token=access, refresh_token=refresh, user=user)


@router.post("/register", response_model=TokenPair)
async def register(payload: UserCreate, response: Response, session: AsyncSession = Depends(get_db)) -> TokenPair:
    user = await user_service.create_user(
        session, email=payload.email, password=payload.password, display_name=payload.display_name
    )
    tokens = await _token_response(session, UserRead.model_validate(user))
    set_auth_cookies(response, tokens.access_token, tokens.refresh_token)
    return tokens


@router.post("/login", response_model=TokenPair)
async def login(payload: UserLogin, response: Response, session: AsyncSession = Depends(get_db)) -> TokenPair:
    user = await user_service.authenticate_user(session, payload.email, payload.password)
    tokens = await _token_response(session, UserRead.model_validate(user))
    set_auth_cookies(response, tokens.access_token, tokens.refresh_token)
    return tokens


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    response: Response,
    session: AsyncSession = Depends(get_db),
    refresh_token: str | None = Body(default=None, embed=True),
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> TokenPair:
    raw_token = refresh_token or refresh_cookie
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

    rotated = await refresh_token_service.rotate_refresh_token(session, raw_token)
    if not rotated:
        clear_auth_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    new_refresh, user_id = rotated
    user = await user_service.get_user_by_id(session, user_id)
    if not user:
        await refresh_token_service.revoke_refresh_token(session, new_refresh, reason="user_missing")
        clear_auth_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    user_data = UserRead.model_validate(user)
    access = create_access_token(str(user.id))
    tokens = TokenPair(access_token=access, refresh_token=new_refresh, user=user_data)
    set_auth_cookies(response, tokens.access_token, tokens.refresh_token)
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    session: AsyncSession = Depends(get_db),
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> Response:
    if refresh_cookie:
        await refresh_token_service.revoke_refresh_token(session, refresh_cookie, reason="logout")
    clear_auth_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/sessions", response_model=list[SessionRead])
async def list_sessions(
    include_expired: bool = Query(default=False),
    include_revoked: bool = Query(default=False),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> list[SessionRead]:
    tokens = await refresh_token_service.list_user_tokens(
        session,
        current_user.id,
        include_expired=include_expired,
        include_revoked=include_revoked,
    )
    current_token_id: UUID | None = None
    if refresh_cookie:
        current = await refresh_token_service.get_token_by_value(session, refresh_cookie)
        if current and current.user_id == current_user.id:
            current_token_id = current.id
    return [_serialize_session(token, current_token_id) for token in tokens]


@router.post("/sessions/{token_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    token_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    revoked = await refresh_token_service.revoke_refresh_token_by_id(
        session, current_user.id, token_id, reason="user_revoked"
    )
    if not revoked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
