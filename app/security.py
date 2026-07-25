from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.config import settings


def hash_password(password: str) -> str:
    """Return a salted bcrypt hash for a validated password."""

    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Safely compare a plain password with its stored bcrypt hash."""

    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except (TypeError, ValueError):
        return False


def create_access_token(
    user_id: str,
    *,
    expires_delta: timedelta | None = None,
) -> tuple[str, datetime]:
    """Create a signed, short-lived JWT and return it with its expiry."""

    now = datetime.now(timezone.utc)
    expires_at = now + (
        expires_delta
        or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {
        "sub": user_id,
        "type": "access",
        "iat": now,
        "exp": expires_at,
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return token, expires_at


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode a valid access token or return None for any invalid token."""

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        return None

    if payload.get("type") != "access" or not payload.get("sub"):
        return None
    return payload
