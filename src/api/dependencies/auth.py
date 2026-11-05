from collections.abc import Callable
from uuid import UUID

from fastapi import (
    Depends,
    HTTPException,
    Security,
    status,
)
from fastapi.security import APIKeyCookie
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.security import decode_access_token
from src.db.database import get_db
from src.models.user import User
from src.services.auth_service import AuthService

auth_cookie = APIKeyCookie(
    name=settings.AUTH_COOKIE_NAME,
    auto_error=False,
)


def get_current_user_id(
    token: str | None = Security(auth_cookie),
) -> UUID:

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


def get_current_user(
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> User:

    auth_service = AuthService(db)

    return auth_service.get_authenticated_user(user_id)


def require_roles(*allowed_roles: str) -> Callable[..., User]:

    if not allowed_roles:
        raise ValueError("At least one role must be specified.")

    def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:

        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource.",
            )

        return current_user

    return role_checker
