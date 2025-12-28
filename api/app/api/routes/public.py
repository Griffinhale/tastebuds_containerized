"""Public endpoints for shared menu access."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schema.menu import DraftMenuRead, MenuLineageRead, PublicMenuRead
from app.services import menu_service

router = APIRouter()


@router.get("/menus/{slug}", response_model=PublicMenuRead)
async def read_public_menu(slug: str, session: AsyncSession = Depends(get_db)) -> PublicMenuRead:
    """Fetch a public menu by slug."""
    menu = await menu_service.get_menu_by_slug(session, slug)
    if not menu:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu not found")
    return PublicMenuRead.model_validate(menu)


@router.get("/menus/draft/{token}", response_model=DraftMenuRead)
async def read_draft_menu(token: str, session: AsyncSession = Depends(get_db)) -> DraftMenuRead:
    """Fetch a draft menu by share token."""
    menu, share_token = await menu_service.get_menu_by_share_token(session, token)
    return DraftMenuRead(
        menu=PublicMenuRead.model_validate(menu),
        share_token_id=share_token.id,
        share_token_expires_at=share_token.expires_at,
    )


@router.get("/menus/{slug}/lineage", response_model=MenuLineageRead)
async def read_public_menu_lineage(
    slug: str, session: AsyncSession = Depends(get_db)
) -> MenuLineageRead:
    """Fetch lineage metadata for a public menu."""
    menu = await menu_service.get_menu_by_slug(session, slug)
    if not menu:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu not found")
    source_menu, source_note, forks = await menu_service.get_menu_lineage_summary(
        session, menu.id, include_private=False
    )
    source_payload = None
    if source_menu:
        source_payload = {"menu": source_menu, "note": source_note}
    return MenuLineageRead(source_menu=source_payload, forked_menus=forks, fork_count=len(forks))
