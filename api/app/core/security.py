"""JWT and password hashing helpers for auth flows."""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_token(subject: str, expires_delta: timedelta, token_type: str) -> str:
    """Create a signed JWT for the given subject and token type."""
    now = datetime.utcnow()
    payload: Dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str) -> str:
    """Create an access token with the configured TTL."""
    delta = timedelta(minutes=settings.access_token_expires_minutes)
    return create_token(subject, delta, "access")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using the configured context."""
    return pwd_context.hash(password)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode a JWT and return its payload if valid."""
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
