from fastapi import status
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID
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
from src.api.dependencies.auth import get_current_user_id

router = APIRouter()


def get_auth_controller(
    db: Session = Depends(get_db),
) -> AuthController:

    auth_service = AuthService(db)

    return AuthController(auth_service)


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


@router.post("/logout")
def logout(
    controller: AuthController = Depends(get_auth_controller),
):
    return controller.logout()
