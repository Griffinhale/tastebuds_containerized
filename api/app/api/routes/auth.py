from fastapi import APIRouter, Body, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.schema.auth import TokenPair
from app.schema.user import UserCreate, UserLogin, UserRead
from app.services import user_service

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
    response.delete_cookie(ACCESS_COOKIE_NAME, path="/")
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/")


def _token_response(user: UserRead) -> TokenPair:
    access = create_access_token(str(user.id))
    refresh = create_refresh_token(str(user.id))
    return TokenPair(access_token=access, refresh_token=refresh, user=user)


@router.post("/register", response_model=TokenPair)
async def register(
    payload: UserCreate, response: Response, session: AsyncSession = Depends(get_db)
) -> TokenPair:
    user = await user_service.create_user(
        session, email=payload.email, password=payload.password, display_name=payload.display_name
    )
    tokens = _token_response(UserRead.model_validate(user))
    set_auth_cookies(response, tokens.access_token, tokens.refresh_token)
    return tokens


@router.post("/login", response_model=TokenPair)
async def login(payload: UserLogin, response: Response, session: AsyncSession = Depends(get_db)) -> TokenPair:
    user = await user_service.authenticate_user(session, payload.email, payload.password)
    tokens = _token_response(UserRead.model_validate(user))
    set_auth_cookies(response, tokens.access_token, tokens.refresh_token)
    return tokens


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    response: Response,
    session: AsyncSession = Depends(get_db),
    refresh_token: str | None = Body(default=None, embed=True),
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> TokenPair:
    token = refresh_token or refresh_cookie
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user = await user_service.get_user_by_id(session, payload.get("sub"))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    tokens = _token_response(UserRead.model_validate(user))
    set_auth_cookies(response, tokens.access_token, tokens.refresh_token)
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> Response:
    clear_auth_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
