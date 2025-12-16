from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.security import create_access_token, create_refresh_token
from app.schema.auth import TokenPair
from app.schema.user import UserCreate, UserLogin, UserRead
from app.services import user_service

router = APIRouter()


def _token_response(user: UserRead) -> TokenPair:
    access = create_access_token(str(user.id))
    refresh = create_refresh_token(str(user.id))
    return TokenPair(access_token=access, refresh_token=refresh, user=user)


@router.post("/register", response_model=TokenPair)
async def register(payload: UserCreate, session: AsyncSession = Depends(get_db)) -> TokenPair:
    user = await user_service.create_user(
        session, email=payload.email, password=payload.password, display_name=payload.display_name
    )
    return _token_response(UserRead.model_validate(user))


@router.post("/login", response_model=TokenPair)
async def login(payload: UserLogin, session: AsyncSession = Depends(get_db)) -> TokenPair:
    user = await user_service.authenticate_user(session, payload.email, payload.password)
    return _token_response(UserRead.model_validate(user))
