import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.security import hash_password, hash_token, verify_password
from src.models import AuthAccount, User
from src.models.email_verification_token import EmailVerificationToken
from src.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    ResendVerificationEmailRequest,
)
from src.services.email_verification_service import EmailVerificationService

logger = logging.getLogger(__name__)


class AuthService:

    RESEND_COOLDOWN_SECONDS = 60

    def __init__(self, db: Session):
        self.db = db

    # --------------------------------------------------
    # REGISTER
    # --------------------------------------------------

    def register(self, payload: RegisterRequest) -> None:

        email = str(payload.email).strip().lower()
        password_hash = hash_password(payload.password)

        raw_token = None
        user_id = None
        verification_email = email
        verification_name = payload.name
        verification_purpose = EmailVerificationService.PURPOSE_INITIAL_EMAIL

        try:
            with self.db.begin():

                existing_user = self.db.scalar(
                    select(User).where(User.email == email).with_for_update()
                )

                if existing_user:
                    google_account = self.db.scalar(
                        select(AuthAccount).where(
                            AuthAccount.user_id == existing_user.id,
                            AuthAccount.provider == "google",
                        )
                    )
                    email_account = self.db.scalar(
                        select(AuthAccount.id).where(
                            AuthAccount.user_id == existing_user.id,
                            AuthAccount.provider == "email",
                        )
                    )

                    if google_account is None or email_account is not None:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="An account with this email already exists.",
                        )

                    self.db.execute(
                        update(EmailVerificationToken)
                        .where(
                            EmailVerificationToken.user_id == existing_user.id,
                            EmailVerificationToken.purpose == "add_email_login",
                            EmailVerificationToken.used_at.is_(None),
                            EmailVerificationToken.revoked_at.is_(None),
                        )
                        .values(revoked_at=datetime.now(timezone.utc))
                    )

                    verification_purpose = "add_email_login"
                    verification_email = existing_user.email
                    verification_name = existing_user.name
                    token_record, raw_token = EmailVerificationService.create_token_record(
                        user_id=existing_user.id,
                        purpose=verification_purpose,
                        pending_password_hash=password_hash,
                    )
                    self.db.add(token_record)
                    user_id = existing_user.id

                else:
                    user = User(
                        name=payload.name,
                        email=email,
                        role=User.ROLE_USER,
                        is_verified=False,
                        is_active=True,
                        is_restricted=False,
                    )

                    self.db.add(user)
                    self.db.flush()

                    auth_account = AuthAccount(
                        user_id=user.id,
                        provider="email",
                        provider_user_id=None,
                        password_hash=password_hash,
                    )

                    self.db.add(auth_account)

                    token_record, raw_token = EmailVerificationService.create_token_record(
                        user_id=user.id,
                    )

                    self.db.add(token_record)

                    user_id = user.id

        except IntegrityError:

            self.db.rollback()
            existing_user = self.db.scalar(select(User.id).where(User.email == email))

            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="An account with this email already exists.",
                )

            raise

        # Send email only after the database transaction commits.
        try:
            EmailVerificationService.send_initial_verification_email(
                email=verification_email,
                name=verification_name,
                raw_token=raw_token,
            )

        except Exception:
            logger.exception(
                "Verification email delivery failed for user_id=%s",
                user_id,
            )

    # --------------------------------------------------
    # VERIFY EMAIL
    # --------------------------------------------------

    def verify_email(self, raw_token: str) -> None:

        token_hash = hash_token(raw_token)
        now = datetime.now(timezone.utc)

        with self.db.begin():

            # Read the token owner first so locks are acquired in User -> Token order.
            token_details = self.db.execute(
                select(EmailVerificationToken.user_id).where(
                    EmailVerificationToken.token_hash == token_hash,
                    EmailVerificationToken.purpose.in_(
                        ("verify_initial_email", "add_email_login")
                    ),
                )
            ).first()

            if token_details is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or already used verification link.",
                )

            token_user_id = token_details[0]

            # Lock the user first.
            user = self.db.scalar(
                select(User).where(User.id == token_user_id).with_for_update()
            )

            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid verification link.",
                )

            # Now lock and revalidate the token.
            token = self.db.scalar(
                select(EmailVerificationToken)
                .where(
                    EmailVerificationToken.token_hash == token_hash,
                    EmailVerificationToken.user_id == user.id,
                    EmailVerificationToken.purpose.in_(
                        ("verify_initial_email", "add_email_login")
                    ),
                    EmailVerificationToken.used_at.is_(None),
                    EmailVerificationToken.revoked_at.is_(None),
                )
                .with_for_update()
            )

            if token is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or already used verification link.",
                )

            if token.expires_at <= now:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Verification link has expired.",
                )

            if token.purpose == "verify_initial_email" and user.is_verified:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email address is already verified.",
                )

            if token.purpose == "add_email_login":
                if not token.pending_password_hash:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid email login verification link.",
                    )

                existing_email_account = self.db.scalar(
                    select(AuthAccount.id).where(
                        AuthAccount.user_id == user.id,
                        AuthAccount.provider == "email",
                    )
                )
                if existing_email_account is not None:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="An email login is already connected to this account.",
                    )

                self.db.add(
                    AuthAccount(
                        user_id=user.id,
                        provider="email",
                        provider_user_id=None,
                        password_hash=token.pending_password_hash,
                    )
                )
                user.is_verified = True
            else:
                user.is_verified = True

            token.used_at = now

    # --------------------------------------------------
    # RESEND VERIFICATION EMAIL
    # --------------------------------------------------

    def resend_verification_email(
        self,
        payload: ResendVerificationEmailRequest,
    ) -> None:

        email = str(payload.email).strip().lower()
        now = datetime.now(timezone.utc)

        raw_token = None
        user_id = None
        user_email = None
        user_name = None
        verification_purpose = None
        pending_password_hash = None

        with self.db.begin():

            # Find and lock the user.
            user = self.db.scalar(
                select(User).where(User.email == email).with_for_update()
            )

            if user is None:
                return

            user_id = user.id
            user_email = user.email
            user_name = user.name

            if user.is_verified:
                verification_purpose = "add_email_login"
                pending_token = self.db.scalar(
                    select(EmailVerificationToken)
                    .where(
                        EmailVerificationToken.user_id == user.id,
                        EmailVerificationToken.purpose == verification_purpose,
                        EmailVerificationToken.used_at.is_(None),
                        EmailVerificationToken.revoked_at.is_(None),
                    )
                    .order_by(EmailVerificationToken.created_at.desc())
                    .limit(1)
                )
                if pending_token is None:
                    return
                pending_password_hash = pending_token.pending_password_hash
                if pending_password_hash is None:
                    return
            else:
                verification_purpose = "verify_initial_email"

            # Check when the most recent verification token was created.
            latest_token_created_at = self.db.scalar(
                select(EmailVerificationToken.created_at)
                .where(
                    EmailVerificationToken.user_id == user.id,
                    EmailVerificationToken.purpose == verification_purpose,
                )
                .order_by(EmailVerificationToken.created_at.desc())
                .limit(1)
            )

            # Apply resend cooldown.
            if latest_token_created_at is not None:

                cooldown_end = latest_token_created_at + timedelta(
                    seconds=self.RESEND_COOLDOWN_SECONDS
                )

                if now < cooldown_end:
                    return

            # Revoke ALL previous unused tokens,
            # regardless of whether they have expired.
            self.db.execute(
                update(EmailVerificationToken)
                .where(
                    EmailVerificationToken.user_id == user.id,
                    EmailVerificationToken.purpose == verification_purpose,
                    EmailVerificationToken.used_at.is_(None),
                    EmailVerificationToken.revoked_at.is_(None),
                )
                .values(revoked_at=now)
            )

            # Generate a new token using existing service logic.
            token_record, raw_token = EmailVerificationService.create_token_record(
                user_id=user.id,
                purpose=verification_purpose,
                pending_password_hash=pending_password_hash,
            )

            self.db.add(token_record)

        # Transaction has committed successfully.
        # Send the email outside the database transaction.
        try:
            EmailVerificationService.send_initial_verification_email(
                email=user_email,
                name=user_name,
                raw_token=raw_token,
                is_resend=True,
            )

        except Exception:
            logger.exception(
                "Resend verification email delivery failed for user_id=%s",
                user_id,
            )

    # --------------------------------------------------
    # LOGIN
    # --------------------------------------------------

    def login(self, payload: LoginRequest) -> User:

        email = str(payload.email).strip().lower()

        user = self.db.scalar(select(User).where(User.email == email))

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        auth_account = self.db.scalar(
            select(AuthAccount).where(
                AuthAccount.user_id == user.id,
                AuthAccount.provider == "email",
            )
        )

        if not auth_account or not auth_account.password_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        is_password_valid = verify_password(
            payload.password,
            auth_account.password_hash,
        )

        if not is_password_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please verify your email address before logging in.",
            )

        if not user.is_active or user.is_restricted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account is currently unavailable.",
            )

        return user

    # --------------------------------------------------
    # GET AUTHENTICATED USER
    # --------------------------------------------------

    def get_authenticated_user(self, user_id: UUID) -> User:

        user = self.db.scalar(select(User).where(User.id == user_id))

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account no longer exists.",
            )

        if not user.is_active or user.is_restricted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account is currently unavailable.",
            )

        return user
