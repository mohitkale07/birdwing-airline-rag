from fastapi import HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse, Response

from src.core.cookies import set_auth_cookie
from src.core.config import settings
from src.core.security import create_access_token
from src.models.user import User
from src.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    ResendVerificationEmailRequest,
    VerifyEmailRequest,
)
from src.services.auth_service import AuthService
from src.services.google_oauth_service import GoogleOAuthService


class AuthController:

    def __init__(
        self,
        auth_service: AuthService,
        google_oauth_service: GoogleOAuthService,
    ):
        self.auth_service = auth_service
        self.google_oauth_service = google_oauth_service

    def google_login(self) -> RedirectResponse:
        authorization_url, signed_state = (
            self.google_oauth_service.create_authorization_url()
        )
        response = RedirectResponse(authorization_url, status_code=302)
        response.set_cookie(
            key=GoogleOAuthService.STATE_COOKIE_NAME,
            value=signed_state,
            max_age=GoogleOAuthService.STATE_TTL_SECONDS,
            httponly=True,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite="lax",
            path=settings.AUTH_COOKIE_PATH,
        )
        return response

    def google_link(self, user: User) -> RedirectResponse:
        authorization_url, signed_state = (
            self.google_oauth_service.create_authorization_url(user.id)
        )
        response = RedirectResponse(authorization_url, status_code=302)
        response.set_cookie(
            key=GoogleOAuthService.STATE_COOKIE_NAME,
            value=signed_state,
            max_age=GoogleOAuthService.STATE_TTL_SECONDS,
            httponly=True,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite="lax",
            path=settings.AUTH_COOKIE_PATH,
        )
        return response

    def google_callback(
        self,
        code: str | None,
        state: str | None,
        signed_state: str | None,
        provider_error: str | None = None,
    ) -> Response:
        if provider_error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google authorization was not completed.",
            )
        if not code or not state or not signed_state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google authorization response is incomplete.",
            )

        intent, linked_user_id = self.google_oauth_service.verify_state(
            state,
            signed_state,
        )
        identity = self.google_oauth_service.verify_authorization_code(code)
        user = self.google_oauth_service.complete_authentication(
            identity,
            linked_user_id=linked_user_id,
        )

        response = JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": (
                    "Google account linked successfully."
                    if intent == "link"
                    else "Google login successful."
                ),
                "user": {
                    "id": str(user.id),
                    "name": user.name,
                    "email": user.email,
                },
            },
        )
        if intent == "login":
            set_auth_cookie(response, create_access_token(user.id))
        response.delete_cookie(
            key=GoogleOAuthService.STATE_COOKIE_NAME,
            path=settings.AUTH_COOKIE_PATH,
            secure=settings.AUTH_COOKIE_SECURE,
            httponly=True,
            samesite="lax",
        )
        return response

    def google_unlink(self, user: User) -> JSONResponse:
        self.google_oauth_service.unlink_google_account(user.id)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": "Google account unlinked successfully.",
            },
        )

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
