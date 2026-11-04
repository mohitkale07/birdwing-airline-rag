from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

from src.core.config import settings
from src.core.security import create_access_token
from src.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    ResendVerificationEmailRequest,
    VerifyEmailRequest,
)
from src.services.auth_service import AuthService


class AuthController:

    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service

    # --------------------------------------------------
    # REGISTER
    # --------------------------------------------------

    def register(self, payload: RegisterRequest) -> JSONResponse:

        self.auth_service.register(payload)

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "success": True,
                "message": (
                    "Account created successfully. "
                    "Please check your email to verify your account."
                ),
            },
        )

    # --------------------------------------------------
    # VERIFY EMAIL
    # --------------------------------------------------

    def verify_email(self, payload: VerifyEmailRequest) -> JSONResponse:

        self.auth_service.verify_email(payload.token)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": "Email verified successfully.",
            },
        )

    def resend_verification_email(
        self,
        payload: ResendVerificationEmailRequest,
    ) -> JSONResponse:

        self.auth_service.resend_verification_email(payload)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": (
                    "If the account exists and is not verified, "
                    "a new verification email will be sent."
                ),
            },
        )

    # --------------------------------------------------
    # LOGIN
    # --------------------------------------------------

    def login(self, payload: LoginRequest) -> JSONResponse:

        user = self.auth_service.login(payload)

        access_token = create_access_token(user.id)

        response = JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": "Login successful.",
            },
        )

        response.set_cookie(
            key=settings.AUTH_COOKIE_NAME,
            value=access_token,
            httponly=settings.AUTH_COOKIE_HTTP_ONLY,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAME_SITE,
            path=settings.AUTH_COOKIE_PATH,
            domain=settings.AUTH_COOKIE_DOMAIN,
            max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

        return response

    # --------------------------------------------------
    # LOGOUT
    # --------------------------------------------------

    def logout(self) -> JSONResponse:

        response = JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": "Logged out successfully.",
            },
        )

        response.delete_cookie(
            key=settings.AUTH_COOKIE_NAME,
            path=settings.AUTH_COOKIE_PATH,
            domain=settings.AUTH_COOKIE_DOMAIN,
            secure=settings.AUTH_COOKIE_SECURE,
            httponly=settings.AUTH_COOKIE_HTTP_ONLY,
            samesite=settings.AUTH_COOKIE_SAME_SITE,
        )

        return response
