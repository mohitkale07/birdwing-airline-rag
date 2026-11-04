from fastapi import Response

from src.core.config import settings


def set_auth_cookie(
    response: Response,
    token: str,
) -> None:
    """
    Set the JWT access token in an HttpOnly cookie.
    """

    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=token,
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=settings.AUTH_COOKIE_HTTP_ONLY,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAME_SITE,
        path=settings.AUTH_COOKIE_PATH,
        domain=settings.AUTH_COOKIE_DOMAIN,
    )


def clear_auth_cookie(response: Response) -> None:
    """
    Remove the authentication cookie during logout.
    """

    response.delete_cookie(
        key=settings.AUTH_COOKIE_NAME,
        httponly=settings.AUTH_COOKIE_HTTP_ONLY,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAME_SITE,
        path=settings.AUTH_COOKIE_PATH,
        domain=settings.AUTH_COOKIE_DOMAIN,
    )
