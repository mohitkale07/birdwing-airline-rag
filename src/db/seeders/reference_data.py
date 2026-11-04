import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import AuthAccount, EmailVerificationToken, User


@dataclass(frozen=True)
class DemoUser:
    name: str
    email: str
    is_verified: bool
    is_active: bool
    is_restricted: bool
    google_user_id: str
    verification_purpose: str | None = None


DEMO_USERS = (
    DemoUser(
        name="Alex Morgan",
        email="alex.morgan@example.test",
        is_verified=True,
        is_active=True,
        is_restricted=False,
        google_user_id="demo-google-alex-morgan",
    ),
    DemoUser(
        name="Jordan Lee",
        email="jordan.lee@example.test",
        is_verified=False,
        is_active=True,
        is_restricted=False,
        google_user_id="demo-google-jordan-lee",
        verification_purpose="verify_initial_email",
    ),
    DemoUser(
        name="Taylor Quinn",
        email="taylor.quinn@example.test",
        is_verified=True,
        is_active=True,
        is_restricted=True,
        google_user_id="demo-google-taylor-quinn",
    ),
)


def seed_reference_data(session: Session) -> dict[str, int]:
    """Insert missing demo users and their related auth and verification rows."""
    created = {
        "users": 0,
        "auth_accounts": 0,
        "verification_tokens": 0,
    }

    for demo_user in DEMO_USERS:
        user = session.scalar(
            select(User).where(User.email == demo_user.email)
        )
        if user is None:
            user = User(
                name=demo_user.name,
                email=demo_user.email,
                is_verified=demo_user.is_verified,
                is_active=demo_user.is_active,
                is_restricted=demo_user.is_restricted,
            )
            session.add(user)
            session.flush()
            created["users"] += 1

        google_account = session.scalar(
            select(AuthAccount).where(
                AuthAccount.user_id == user.id,
                AuthAccount.provider == "google",
            )
        )
        if google_account is None:
            session.add(
                AuthAccount(
                    user_id=user.id,
                    provider="google",
                    provider_user_id=demo_user.google_user_id,
                )
            )
            created["auth_accounts"] += 1

        if demo_user.verification_purpose is None:
            continue

        token_hash = hashlib.sha256(
            f"demo-seed:{demo_user.email}".encode("utf-8")
        ).hexdigest()
        token = session.scalar(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token_hash == token_hash
            )
        )
        if token is None:
            session.add(
                EmailVerificationToken(
                    user_id=user.id,
                    token_hash=token_hash,
                    purpose=demo_user.verification_purpose,
                    expires_at=datetime.now(timezone.utc) + timedelta(days=7),
                )
            )
            created["verification_tokens"] += 1

    return created