"""Shared helpers for API tests."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from httpx import AsyncClient


@dataclass(slots=True)
class AuthContext:
    """Authenticated client context for API tests."""

    client: AsyncClient
    user: dict[str, Any]
    email: str
    password: str

    @property
    def user_id(self) -> str:
        return str(self.user["id"])


async def register_and_login(client: AsyncClient, *, prefix: str = "user") -> AuthContext:
    """Register and log in a new user, returning the auth context."""
    suffix = uuid.uuid4().hex[:8]
    email = f"{prefix}_{suffix}@example.com"
    password = "supersecret123"
    creds = {"email": email, "password": password, "display_name": f"{prefix.title()} {suffix}"}

    register_res = await client.post("/api/auth/register", json=creds)
    assert register_res.status_code == 200
    user = register_res.json()["user"]

    login_res = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert login_res.status_code == 200

    return AuthContext(client=client, user=user, email=email, password=password)
