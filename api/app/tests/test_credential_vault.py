"""Tests for credential vault storage, expiry, and retrieval."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.user import User
from app.services.credential_vault import credential_vault


@pytest.mark.asyncio
async def test_credential_vault_store_and_read(session):
    user = User(email="vault@example.com", hashed_password="pw")
    session.add(user)
    await session.commit()
    await session.refresh(user)

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    await credential_vault.store_secret(
        session,
        user_id=user.id,
        provider="spotify",
        secret_payload={"access_token": "abc123"},
        expires_at=expires_at,
    )

    secret = await credential_vault.get_secret(session, user_id=user.id, provider="spotify")
    assert secret == {"access_token": "abc123"}


@pytest.mark.asyncio
async def test_credential_vault_respects_expiry_and_clear(session):
    user = User(email="expired@example.com", hashed_password="pw")
    session.add(user)
    await session.commit()
    await session.refresh(user)

    await credential_vault.store_secret(
        session,
        user_id=user.id,
        provider="arr",
        secret_payload={"token": "stale"},
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )

    secret = await credential_vault.get_secret(session, user_id=user.id, provider="arr")
    assert secret is None

    await credential_vault.clear_on_failure(session, user_id=user.id, provider="arr", error="expired")
    cleared = await credential_vault.get_secret(session, user_id=user.id, provider="arr", allow_expired=True)
    assert cleared is None
