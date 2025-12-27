"""Public endpoints for shared menu access."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schema.menu import PublicMenuRead
from app.services import menu_service

router = APIRouter()


@router.get("/menus/{slug}", response_model=PublicMenuRead)
async def read_public_menu(slug: str, session: AsyncSession = Depends(get_db)) -> PublicMenuRead:
    """Fetch a public menu by slug."""
    menu = await menu_service.get_menu_by_slug(session, slug)
    if not menu:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu not found")
    return PublicMenuRead.model_validate(menu)
