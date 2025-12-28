"""Integration management and export endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models.user import User
from app.schema.integrations import (
    IntegrationCredentialUpdate,
    IntegrationIngestEventRead,
    IntegrationStatusRead,
    IntegrationSyncRequest,
    IntegrationWebhookTokenRead,
    SpotifyExportRequest,
    SpotifyExportResponse,
)
from app.services import integration_queue_service, integration_service, menu_service, spotify_service
from app.services.task_queue import task_queue

router = APIRouter()


@router.get("", response_model=list[IntegrationStatusRead])
async def list_integrations(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[IntegrationStatusRead]:
    """List integration status for the current user."""
    return await integration_service.list_statuses(session, user_id=current_user.id)


@router.post("/{provider}/credentials", response_model=IntegrationStatusRead)
async def store_integration_credentials(
    provider: str,
    payload: IntegrationCredentialUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IntegrationStatusRead:
    """Store headless credentials for an integration provider."""
    try:
        await integration_service.store_credentials(
            session,
            user_id=current_user.id,
            provider=provider,
            payload=payload.payload,
            expires_at=payload.expires_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    statuses = await integration_service.list_statuses(session, user_id=current_user.id)
    status_map = {status.provider.value: status for status in statuses}
    if provider not in status_map:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")
    return status_map[provider]


@router.delete(
    "/{provider}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def disconnect_integration(
    provider: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Disconnect a provider and delete stored credentials."""
    try:
        await integration_service.delete_credentials(session, user_id=current_user.id, provider=provider)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{provider}/rotate")
async def rotate_integration_credentials(
    provider: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Trigger credential rotation for a provider."""
    try:
        integration_service.get_provider_config(provider)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return await task_queue.enqueue_credential_rotation(
        provider=provider,
        user_id=current_user.id,
        requested_by=str(current_user.id),
    )


@router.get("/spotify/authorize")
async def spotify_authorize(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return a Spotify OAuth authorization URL."""
    state = spotify_service.build_state_token(current_user.id)
    return {"authorization_url": spotify_service.build_authorize_url(state)}


@router.get("/spotify/callback")
async def spotify_callback(
    code: str,
    state: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RedirectResponse:
    """Handle the Spotify OAuth callback."""
    state_user_id = spotify_service.decode_state_token(state)
    if state_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Spotify state mismatch")
    payload = await spotify_service.exchange_code_for_token(code)
    await spotify_service.store_tokens(session, user_id=current_user.id, payload=payload)
    redirect_target = f"{settings.app_base_url.rstrip('/')}/integrations?status=spotify_connected"
    return RedirectResponse(url=redirect_target, status_code=status.HTTP_302_FOUND)


@router.post("/spotify/menus/{menu_id}/export", response_model=SpotifyExportResponse)
async def spotify_export_menu(
    menu_id: uuid.UUID,
    payload: SpotifyExportRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SpotifyExportResponse:
    """Export a menu's music courses to Spotify."""
    menu = await menu_service.get_menu(session, menu_id, owner_id=current_user.id)
    return await spotify_service.export_menu(
        session,
        user_id=current_user.id,
        menu=menu,
        payload=payload,
    )


@router.post("/arr/webhook-token", response_model=IntegrationWebhookTokenRead)
async def create_arr_webhook_token(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IntegrationWebhookTokenRead:
    """Generate a new Arr webhook token."""
    token, record = await integration_service.create_webhook_token(
        session, user_id=current_user.id, provider="arr"
    )
    return IntegrationWebhookTokenRead(
        provider=record.provider,
        webhook_url=integration_service.build_webhook_url("arr", token),
        token_prefix=record.token_prefix,
    )


@router.post("/arr/webhook/{token}")
async def arr_webhook(
    token: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Receive Arr webhook events and enqueue ingestion."""
    record = await integration_service.resolve_webhook_token(session, provider="arr", token=token)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook token not found")
    payload = await request.json()
    source_ip = request.client.host if request.client else None
    return await task_queue.enqueue_webhook_event(
        provider="arr",
        payload=payload,
        event_type=payload.get("eventType"),
        source_ip=source_ip,
        user_id=str(record.user_id),
    )


@router.get("/arr/queue", response_model=list[IntegrationIngestEventRead])
async def list_arr_queue(
    status_filter: str | None = None,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[IntegrationIngestEventRead]:
    """List Arr ingest queue events for the current user."""
    try:
        events = await integration_queue_service.list_ingest_events(
            session,
            user_id=current_user.id,
            provider="arr",
            status_filter=status_filter,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return [IntegrationIngestEventRead.model_validate(event) for event in events]


@router.post("/arr/queue/{event_id}/ingest", response_model=IntegrationIngestEventRead)
async def ingest_arr_event(
    event_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IntegrationIngestEventRead:
    """Ingest a queued Arr event."""
    event = await integration_queue_service.ingest_event(
        session,
        user_id=current_user.id,
        event_id=event_id,
    )
    return IntegrationIngestEventRead.model_validate(event)


@router.post("/arr/queue/{event_id}/dismiss", response_model=IntegrationIngestEventRead)
async def dismiss_arr_event(
    event_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IntegrationIngestEventRead:
    """Dismiss a queued Arr event."""
    event = await integration_queue_service.dismiss_event(
        session,
        user_id=current_user.id,
        event_id=event_id,
    )
    return IntegrationIngestEventRead.model_validate(event)


@router.post("/{provider}/sync")
async def trigger_integration_sync(
    provider: str,
    payload: IntegrationSyncRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Queue a background sync for supported integrations."""
    if provider not in {"jellyfin", "plex"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported sync provider")
    return await task_queue.enqueue_sync_task(
        provider=provider,
        external_id=payload.external_id,
        action=payload.action,
        force_refresh=payload.force_refresh,
        requested_by=str(current_user.id),
    )
