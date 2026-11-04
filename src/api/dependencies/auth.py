from uuid import UUID

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyCookie

from src.core.config import settings
from src.core.security import decode_access_token

auth_cookie = APIKeyCookie(name=settings.AUTH_COOKIE_NAME, auto_error=False)


def get_current_user_id(token: str | None = Security(auth_cookie)) -> UUID:

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
        )

    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
        )

    try:
        return UUID(payload["sub"])

    except (ValueError, TypeError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        )
