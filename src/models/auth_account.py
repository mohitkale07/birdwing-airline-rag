import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.database import Base

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.user import User


class AuthAccount(Base):
    __tablename__ = "auth_accounts"

    __table_args__ = (
        # A provider identity must be unique.
        UniqueConstraint(
            "provider",
            "provider_user_id",
            name="uq_auth_provider_user_id",
        ),
        # Only supported providers are allowed.
        CheckConstraint(
            "provider IN ('email', 'google')",
            name="ck_auth_provider",
        ),
        # Credentials depend on the provider.
        CheckConstraint(
            """
            (
                provider = 'email'
                AND provider_user_id IS NULL
                AND password_hash IS NOT NULL
            )
            OR
            (
                provider = 'google'
                AND provider_user_id IS NOT NULL
                AND password_hash IS NULL
            )
            """,
            name="ck_auth_provider_credentials",
        ),
        # A user can have only one email authentication account.
        Index(
            "uq_auth_email_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("provider = 'email'"),
        ),
        # A user can have only one Google authentication account.
        Index(
            "uq_auth_google_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("provider = 'google'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    provider: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # Google account's stable identifier (Google's sub claim).
    # NULL for email/password authentication.
    provider_user_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Argon2 password hash.
    # NULL for Google authentication.
    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        back_populates="auth_accounts",
    )
