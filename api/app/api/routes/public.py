from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schema.menu import MenuRead
from app.services import menu_service

router = APIRouter()


@router.get("/menus/{slug}", response_model=MenuRead)
async def read_public_menu(slug: str, session: AsyncSession = Depends(get_db)) -> MenuRead:
    menu = await menu_service.get_menu_by_slug(session, slug)
    if not menu:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu not found")
    return menu
