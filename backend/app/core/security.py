"""Security utilities for password hashing, JWT access tokens, and refresh tokens."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError

from app.core.config import get_settings

password_hasher = PasswordHasher()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Verify a plaintext password against an Argon2id hash."""
    try:
        return password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHash):
        return False


def create_access_token(
    *,
    subject: str,
    role: str | None = None,
    company_id: str | None = None,
    expires_minutes: int | None = None,
) -> tuple[str, int, datetime]:
    settings = get_settings()
    now = datetime.now(UTC)
    expires_in_minutes = expires_minutes or settings.access_token_expire_minutes
    expires_at = now + timedelta(minutes=expires_in_minutes)
    jti = str(uuid.uuid4())
    payload: dict[str, Any] = {
        "sub": subject,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": jti,
    }
    if role is not None:
        payload["role"] = role
    if company_id is not None:
        payload["company_id"] = company_id

    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_in_minutes * 60, expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["sub", "type", "iat", "exp", "jti"]},
    )


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_temporary_password(length: int = 20) -> str:
    """Generate a temporary password for bootstrap/reset flows.

    The password is returned only over authenticated API responses; callers
    must not email or log it.
    """
    # URL-safe token gives high entropy and avoids ambiguous formatting.
    return secrets.token_urlsafe(max(16, length))[:length]
