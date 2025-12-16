from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings

app = FastAPI(title=settings.app_name)
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health", tags=["internal"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
