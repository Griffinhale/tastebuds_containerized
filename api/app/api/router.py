"""API router composition for all route groups."""

from fastapi import APIRouter

from .routes import (
    auth,
    automations,
    ingest,
    integrations,
    media,
    menus,
    ops,
    previews,
    public,
    search,
    tags,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, tags=["users"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
api_router.include_router(media.router, tags=["media"])
api_router.include_router(previews.router, tags=["previews"])
api_router.include_router(menus.router, prefix="/menus", tags=["menus"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
api_router.include_router(automations.router, prefix="/automations", tags=["automations"])
api_router.include_router(public.router, prefix="/public", tags=["public"])
api_router.include_router(tags.router, prefix="/tags", tags=["tags"])
api_router.include_router(ops.router, prefix="/ops", tags=["ops"])
