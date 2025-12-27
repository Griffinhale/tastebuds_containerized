"""Service for encrypting and storing user integration credentials."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.credential import UserCredential

logger = logging.getLogger("app.services.credential_vault")


def _utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    now = datetime.utcnow()
    return now if now.tzinfo else now.replace(tzinfo=timezone.utc)


def _derive_key(raw_key: str) -> bytes:
    """Derive a Fernet key from a raw secret."""
    digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


class CredentialVault:
    """Encrypt per-user integration tokens with Fernet and store them server-side."""

    def __init__(self) -> None:
        """Initialize the vault with a stable encryption key."""
        key_material = settings.credential_vault_key or settings.jwt_secret_key
        self._fernet = Fernet(_derive_key(key_material))

    def _encrypt(self, payload: dict[str, Any]) -> str:
        """Encrypt a payload for storage."""
        encoded = json.dumps(payload, default=str).encode("utf-8")
        return self._fernet.encrypt(encoded).decode("utf-8")

    def _decrypt(self, token: str) -> dict[str, Any] | None:
        """Decrypt stored payloads, returning None on failure."""
        try:
            plaintext = self._fernet.decrypt(token.encode("utf-8"))
        except InvalidToken:
            return None
        try:
            return json.loads(plaintext)
        except Exception:
            return None

    async def store_secret(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        provider: str,
        secret_payload: dict[str, Any],
        expires_at: datetime | None = None,
        error: str | None = None,
    ) -> UserCredential:
        """Create or update a stored secret for a provider."""
        encrypted = self._encrypt(secret_payload)
        normalized_expiry = expires_at
        if normalized_expiry and normalized_expiry.tzinfo is None:
            normalized_expiry = normalized_expiry.replace(tzinfo=timezone.utc)
        stmt = select(UserCredential).where(UserCredential.user_id == user_id, UserCredential.provider == provider)
        existing = await session.scalar(stmt)
        now = _utcnow()
        if existing:
            existing.encrypted_secret = encrypted
            existing.expires_at = normalized_expiry
            existing.rotated_at = now
            existing.last_error = error
            credential = existing
        else:
            credential = UserCredential(
                user_id=user_id,
                provider=provider,
                encrypted_secret=encrypted,
                expires_at=normalized_expiry,
                rotated_at=now,
                last_error=error,
            )
            session.add(credential)
        await session.commit()
        await session.refresh(credential)
        return credential

    async def get_secret(
        self, session: AsyncSession, *, user_id: uuid.UUID, provider: str, allow_expired: bool = False
    ) -> dict[str, Any] | None:
        """Fetch and decrypt a stored secret if it is still valid."""
        stmt = select(UserCredential).where(UserCredential.user_id == user_id, UserCredential.provider == provider)
        credential = await session.scalar(stmt)
        if not credential:
            return None
        if not allow_expired and credential.expires_at and credential.expires_at < _utcnow():
            return None
        return self._decrypt(credential.encrypted_secret)

    async def clear_on_failure(self, session: AsyncSession, *, user_id: uuid.UUID, provider: str, error: str) -> None:
        """Clear stored secrets after auth failures while tracking the error."""
        stmt = select(UserCredential).where(UserCredential.user_id == user_id, UserCredential.provider == provider)
        credential = await session.scalar(stmt)
        if not credential:
            return
        credential.last_error = error[:490]
        credential.encrypted_secret = ""
        await session.commit()

    def health(self) -> dict[str, Any]:
        """Return a simple encryption/decryption health check payload."""
        try:
            probe = {"status": "ok", "ts": _utcnow().isoformat()}
            encrypted = self._encrypt(probe)
            decrypted = self._decrypt(encrypted)
            healthy = decrypted == probe
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.error("Credential vault health check failed: %s", exc)
            healthy = False
        return {
            "status": "online" if healthy else "degraded",
            "encryption_key_present": bool(settings.credential_vault_key or settings.jwt_secret_key),
        }


credential_vault = CredentialVault()
