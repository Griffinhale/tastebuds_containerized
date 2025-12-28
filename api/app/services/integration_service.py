"""Integration management helpers for provider credentials and status."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.credential import UserCredential
from app.models.integration import IntegrationWebhookToken
from app.schema.integrations import (
    IntegrationAuthType,
    IntegrationCapabilities,
    IntegrationProvider,
    IntegrationStatusRead,
)
from app.services.credential_vault import credential_vault


@dataclass(frozen=True)
class ProviderConfig:
    """Static integration metadata."""

    provider: IntegrationProvider
    display_name: str
    auth_type: IntegrationAuthType
    capabilities: IntegrationCapabilities


PROVIDERS: dict[str, ProviderConfig] = {
    IntegrationProvider.SPOTIFY.value: ProviderConfig(
        provider=IntegrationProvider.SPOTIFY,
        display_name="Spotify",
        auth_type=IntegrationAuthType.OAUTH,
        capabilities=IntegrationCapabilities(supports_export=True),
    ),
    IntegrationProvider.ARR.value: ProviderConfig(
        provider=IntegrationProvider.ARR,
        display_name="Arr Suite",
        auth_type=IntegrationAuthType.API_KEY,
        capabilities=IntegrationCapabilities(supports_webhooks=True),
    ),
    IntegrationProvider.JELLYFIN.value: ProviderConfig(
        provider=IntegrationProvider.JELLYFIN,
        display_name="Jellyfin",
        auth_type=IntegrationAuthType.API_KEY,
        capabilities=IntegrationCapabilities(supports_sync=True),
    ),
    IntegrationProvider.PLEX.value: ProviderConfig(
        provider=IntegrationProvider.PLEX,
        display_name="Plex",
        auth_type=IntegrationAuthType.API_KEY,
        capabilities=IntegrationCapabilities(supports_sync=True),
    ),
}


def _utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    now = datetime.utcnow()
    return now if now.tzinfo else now.replace(tzinfo=timezone.utc)


def _hash_token(token: str) -> str:
    """Hash webhook tokens for lookup."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_provider_config(provider: str) -> ProviderConfig:
    """Return provider configuration or raise ValueError."""
    normalized = provider.lower()
    config = PROVIDERS.get(normalized)
    if not config:
        raise ValueError(f"Unsupported integration provider: {provider}")
    return config


async def list_statuses(session: AsyncSession, *, user_id: uuid.UUID) -> list[IntegrationStatusRead]:
    """Return provider connection status for a user."""
    result = await session.execute(select(UserCredential).where(UserCredential.user_id == user_id))
    credentials = {row.provider: row for row in result.scalars().all()}
    statuses: list[IntegrationStatusRead] = []
    for provider, config in PROVIDERS.items():
        credential = credentials.get(provider)
        connected = False
        status = "missing"
        expires_at = credential.expires_at if credential else None
        rotated_at = credential.rotated_at if credential else None
        last_error = credential.last_error if credential else None
        if credential and credential.encrypted_secret:
            if expires_at and expires_at < _utcnow():
                status = "expired"
            else:
                status = "connected"
                connected = True
        if last_error and status != "connected":
            status = "error"
        webhook_prefix = None
        if config.capabilities.supports_webhooks:
            webhook_prefix = await _get_webhook_prefix(session, user_id=user_id, provider=provider)
        statuses.append(
            IntegrationStatusRead(
                provider=config.provider,
                display_name=config.display_name,
                auth_type=config.auth_type,
                connected=connected,
                status=status,
                expires_at=expires_at,
                rotated_at=rotated_at,
                last_error=last_error,
                webhook_token_prefix=webhook_prefix,
                capabilities=config.capabilities,
            )
        )
    return statuses


async def store_credentials(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    provider: str,
    payload: dict[str, Any],
    expires_at: datetime | None = None,
) -> UserCredential:
    """Store provider credentials in the vault."""
    normalized = get_provider_config(provider).provider.value
    return await credential_vault.store_secret(
        session,
        user_id=user_id,
        provider=normalized,
        secret_payload=payload,
        expires_at=expires_at,
    )


async def delete_credentials(session: AsyncSession, *, user_id: uuid.UUID, provider: str) -> None:
    """Delete provider credentials."""
    normalized = get_provider_config(provider).provider.value
    await session.execute(
        delete(UserCredential).where(
            UserCredential.user_id == user_id,
            UserCredential.provider == normalized,
        )
    )
    await session.execute(
        update(IntegrationWebhookToken)
        .where(
            IntegrationWebhookToken.user_id == user_id,
            IntegrationWebhookToken.provider == normalized,
            IntegrationWebhookToken.revoked_at.is_(None),
        )
        .values(revoked_at=_utcnow())
    )
    await session.commit()


async def create_webhook_token(
    session: AsyncSession, *, user_id: uuid.UUID, provider: str
) -> tuple[str, IntegrationWebhookToken]:
    """Create a new webhook token for a provider."""
    normalized = get_provider_config(provider).provider.value
    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)
    prefix = token[:8]
    await session.execute(
        update(IntegrationWebhookToken)
        .where(
            IntegrationWebhookToken.user_id == user_id,
            IntegrationWebhookToken.provider == normalized,
            IntegrationWebhookToken.revoked_at.is_(None),
        )
        .values(revoked_at=_utcnow())
    )
    record = IntegrationWebhookToken(
        user_id=user_id,
        provider=normalized,
        token_hash=token_hash,
        token_prefix=prefix,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return token, record


async def resolve_webhook_token(
    session: AsyncSession, *, provider: str, token: str
) -> IntegrationWebhookToken | None:
    """Validate a webhook token and return the matching record."""
    token_hash = _hash_token(token)
    normalized = get_provider_config(provider).provider.value
    stmt = select(IntegrationWebhookToken).where(
        IntegrationWebhookToken.provider == normalized,
        IntegrationWebhookToken.token_hash == token_hash,
        IntegrationWebhookToken.revoked_at.is_(None),
    )
    record = await session.scalar(stmt)
    if not record:
        return None
    record.last_used_at = _utcnow()
    await session.commit()
    await session.refresh(record)
    return record


def build_webhook_url(provider: str, token: str) -> str:
    """Compose a webhook URL for a provider."""
    base = settings.app_base_url.rstrip("/")
    prefix = settings.api_prefix.rstrip("/")
    return f"{base}{prefix}/integrations/{provider}/webhook/{token}"


async def _get_webhook_prefix(session: AsyncSession, *, user_id: uuid.UUID, provider: str) -> str | None:
    """Return the active webhook token prefix if one exists."""
    stmt = select(IntegrationWebhookToken).where(
        IntegrationWebhookToken.user_id == user_id,
        IntegrationWebhookToken.provider == provider,
        IntegrationWebhookToken.revoked_at.is_(None),
    )
    record = await session.scalar(stmt)
    return record.token_prefix if record else None
