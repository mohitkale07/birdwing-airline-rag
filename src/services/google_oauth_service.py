import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from uuid import UUID

import httpx
import jwt
from fastapi import HTTPException, status
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.config import settings
from src.models import AuthAccount, User


@dataclass(frozen=True)
class GoogleIdentity:
    provider_user_id: str
    email: str
    name: str | None


class GoogleOAuthService:
    STATE_COOKIE_NAME = "google_oauth_state"
    STATE_TTL_SECONDS = 600
    GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

    def __init__(self, db: Session):
        self.db = db

    def create_authorization_url(
        self,
        linked_user_id: UUID | None = None,
    ) -> tuple[str, str]:
        intent = "link" if linked_user_id is not None else "login"
        nonce = secrets.token_urlsafe(32)
        state_payload = {
            "type": "google_oauth_state",
            "intent": intent,
            "nonce": nonce,
            "exp": datetime.now(timezone.utc)
            + timedelta(seconds=self.STATE_TTL_SECONDS),
        }
        if linked_user_id is not None:
            state_payload["user_id"] = str(linked_user_id)

        signed_state = jwt.encode(
            state_payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        query = urlencode(
            {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "response_type": "code",
                "scope": "openid email profile",
                "state": nonce,
            }
        )
        return f"{self.GOOGLE_AUTHORIZATION_ENDPOINT}?{query}", signed_state

    @staticmethod
    def verify_state(
        state: str,
        signed_state: str,
    ) -> tuple[str, UUID | None]:
        try:
            payload = jwt.decode(
                signed_state,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={
                    "require": ["exp", "intent", "nonce", "type"],
                },
            )
        except jwt.InvalidTokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired Google OAuth state.",
            ) from exc

        intent = payload.get("intent")
        nonce = payload.get("nonce")
        if (
            payload.get("type") != "google_oauth_state"
            or intent not in ("login", "link")
            or not isinstance(nonce, str)
            or not secrets.compare_digest(
                state.encode("utf-8"),
                nonce.encode("utf-8"),
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Google OAuth state.",
            )

        if intent == "login":
            return intent, None

        try:
            linked_user_id = UUID(payload["user_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Google account-linking state.",
            ) from exc

        return intent, linked_user_id

    @staticmethod
    def verify_authorization_code(code: str) -> GoogleIdentity:
        try:
            response = httpx.post(
                GoogleOAuthService.GOOGLE_TOKEN_ENDPOINT,
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
                timeout=10.0,
            )
            response.raise_for_status()
            token_response = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Google authorization could not be completed.",
            ) from exc

        if not isinstance(token_response, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Google returned an invalid authorization response.",
            )

        google_id_token = token_response.get("id_token")
        if not isinstance(google_id_token, str):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google did not return a valid identity token.",
            )

        try:
            claims = id_token.verify_oauth2_token(
                google_id_token,
                GoogleRequest(),
                settings.GOOGLE_CLIENT_ID,
            )
        except (GoogleAuthError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google identity could not be verified.",
            ) from exc

        provider_user_id = claims.get("sub")
        email = claims.get("email")
        if (
            not isinstance(provider_user_id, str)
            or not provider_user_id
            or not isinstance(email, str)
            or not email.strip()
            or claims.get("email_verified") is not True
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google must provide a verified email address.",
            )

        name = claims.get("name")
        return GoogleIdentity(
            provider_user_id=provider_user_id,
            email=email.strip().lower(),
            name=name if isinstance(name, str) else None,
        )

    def complete_authentication(
        self,
        identity: GoogleIdentity,
        linked_user_id: UUID | None = None,
    ) -> User:
        try:
            with self.db.begin():
                google_account = self.db.scalar(
                    select(AuthAccount).where(
                        AuthAccount.provider == "google",
                        AuthAccount.provider_user_id == identity.provider_user_id,
                    )
                )

                if google_account is not None:
                    if (
                        linked_user_id is not None
                        and google_account.user_id != linked_user_id
                    ):
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="This Google account is linked to another user.",
                        )
                    user = self.db.scalar(
                        select(User)
                        .where(User.id == google_account.user_id)
                        .with_for_update()
                    )
                    if user is None:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="The account linked to Google no longer exists.",
                        )
                    user.is_verified = True
                elif linked_user_id is not None:
                    user = self.db.scalar(
                        select(User)
                        .where(User.id == linked_user_id)
                        .with_for_update()
                    )
                    if user is None:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="The account to link no longer exists.",
                        )
                    existing_google_account = self.db.scalar(
                        select(AuthAccount.id).where(
                            AuthAccount.user_id == user.id,
                            AuthAccount.provider == "google",
                        )
                    )
                    if existing_google_account is not None:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="A Google account is already linked.",
                        )
                    self.db.add(
                        AuthAccount(
                            user_id=user.id,
                            provider="google",
                            provider_user_id=identity.provider_user_id,
                        )
                    )
                else:
                    user = self.db.scalar(
                        select(User)
                        .where(User.email == identity.email)
                        .with_for_update()
                    )
                    if user is None:
                        user = User(
                            name=identity.name,
                            email=identity.email,
                            role=User.ROLE_USER,
                            is_verified=True,
                            is_active=True,
                            is_restricted=False,
                        )
                        self.db.add(user)
                        self.db.flush()
                    else:
                        existing_google_account = self.db.scalar(
                            select(AuthAccount.id).where(
                                AuthAccount.user_id == user.id,
                                AuthAccount.provider == "google",
                            )
                        )
                        if existing_google_account is not None:
                            raise HTTPException(
                                status_code=status.HTTP_409_CONFLICT,
                                detail="A different Google account is already linked.",
                            )
                        user.is_verified = True

                    self.db.add(
                        AuthAccount(
                            user_id=user.id,
                            provider="google",
                            provider_user_id=identity.provider_user_id,
                        )
                    )

                if not user.is_active or user.is_restricted:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Your account is currently unavailable.",
                    )
        except IntegrityError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The Google account conflicts with an existing account.",
            ) from exc

        return user

    def unlink_google_account(self, user_id: UUID) -> None:
        google_account = self.db.scalar(
            select(AuthAccount).where(
                AuthAccount.user_id == user_id,
                AuthAccount.provider == "google",
            )
        )
        if google_account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Google account is linked.",
            )

        another_auth_account = self.db.scalar(
            select(AuthAccount.id).where(
                AuthAccount.user_id == user_id,
                AuthAccount.id != google_account.id,
            )
        )
        if another_auth_account is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Add another sign-in method before unlinking Google.",
            )

        self.db.delete(google_account)
        self.db.commit()
