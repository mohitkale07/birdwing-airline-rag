import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from src.core.config import settings

password_hasher = PasswordHash.recommended()


# --------------------------------------------------
# Password utilities
# --------------------------------------------------


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


# --------------------------------------------------
# Secure random token utilities
# --------------------------------------------------


def generate_secure_token() -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Return the SHA-256 hash of a token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# --------------------------------------------------
# JWT access token utilities
# --------------------------------------------------


def create_access_token(
    user_id: UUID,
    expires_in: timedelta | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + (
        expires_in or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": expires_at,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "type": "access",
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
            options={
                "require": [
                    "sub",
                    "iat",
                    "exp",
                    "iss",
                    "aud",
                    "type",
                ]
            },
        )

        if payload.get("type") != "access":
            return None

        return payload

    except jwt.InvalidTokenError:
        return None
