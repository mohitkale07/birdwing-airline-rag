from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.controllers.auth_controller import AuthController
from src.db.database import get_db
from src.models.user import User
from src.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    ResendVerificationEmailRequest,
    VerifyEmailRequest,
)
from src.services.auth_service import AuthService
from src.services.google_oauth_service import GoogleOAuthService
from src.api.dependencies.auth import (
    get_current_user,
    require_roles,
)

router = APIRouter()


def get_auth_controller(
    db: Session = Depends(get_db),
) -> AuthController:

    auth_service = AuthService(db)
    google_oauth_service = GoogleOAuthService(db)

    return AuthController(auth_service, google_oauth_service)


@router.get("/google/login")
def google_login(
    controller: AuthController = Depends(get_auth_controller),
):
    return controller.google_login()


@router.get("/google/callback")
def google_callback(
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    controller: AuthController = Depends(get_auth_controller),
):
    return controller.google_callback(
        code=code,
        state=state,
        signed_state=request.cookies.get(
            GoogleOAuthService.STATE_COOKIE_NAME,
        ),
        provider_error=error,
    )


@router.post("/google/link")
def google_link(
    current_user: User = Depends(get_current_user),
    controller: AuthController = Depends(get_auth_controller),
):
    return controller.google_link(current_user)


@router.delete("/google/unlink")
def google_unlink(
    current_user: User = Depends(get_current_user),
    controller: AuthController = Depends(get_auth_controller),
):
    return controller.google_unlink(current_user)


@router.post("/register", status_code=201)
def register(
    payload: RegisterRequest,
    controller: AuthController = Depends(get_auth_controller),
):
    return controller.register(payload)


@router.post("/login")
def login(
    payload: LoginRequest,
    controller: AuthController = Depends(get_auth_controller),
):
    return controller.login(payload)


@router.post("/verify-email")
def verify_email(
    payload: VerifyEmailRequest,
    controller: AuthController = Depends(get_auth_controller),
):
    return controller.verify_email(payload)


@router.post("/resend-verification-email")
def resend_verification_email(
    payload: ResendVerificationEmailRequest,
    controller: AuthController = Depends(get_auth_controller),
):
    return controller.resend_verification_email(payload)


@router.get("/admin/dashboard")
def admin_dashboard(
    current_user: User = Depends(require_roles(User.ROLE_ADMIN)),
):
    return {
        "message": "Welcome to the admin dashboard.",
        "user_id": str(current_user.id),
        "role": current_user.role,
    }


@router.get("/me")
def me(
    current_user: User = Depends(get_current_user),
):
    return {
        "id": str(current_user.id),
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "is_verified": current_user.is_verified,
    }


@router.get("/moderation/dashboard")
def moderation_dashboard(
    current_user: User = Depends(
        require_roles(
            User.ROLE_ADMIN,
            "moderator",
        )
    ),
):
    return {
        "message": "Access granted.",
        "role": current_user.role,
    }


@router.post("/logout")
def logout(
    controller: AuthController = Depends(get_auth_controller),
):
    return controller.logout()
