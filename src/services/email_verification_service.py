from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl
from uuid import UUID

from src.core.config import settings
from src.core.security import generate_secure_token, hash_token
from src.models.email_verification_token import EmailVerificationToken
from src.services.email_service import email_service


class EmailVerificationService:

    PURPOSE_INITIAL_EMAIL = "verify_initial_email"

    # --------------------------------------------------
    # CREATE VERIFICATION TOKEN
    # --------------------------------------------------

    @staticmethod
    def create_token_record(
        user_id: UUID,
    ) -> tuple[EmailVerificationToken, str]:

        raw_token = generate_secure_token()
        token_hash = hash_token(raw_token)

        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.EMAIL_VERIFICATION_EXPIRE_MINUTES
        )

        token_record = EmailVerificationToken(
            user_id=user_id,
            token_hash=token_hash,
            purpose=EmailVerificationService.PURPOSE_INITIAL_EMAIL,
            expires_at=expires_at,
        )

        return token_record, raw_token

    # --------------------------------------------------
    # BUILD VERIFICATION URL
    # --------------------------------------------------

    @staticmethod
    def build_verification_url(raw_token: str) -> str:

        url = urlsplit(settings.EMAIL_VERIFICATION_URL)

        query_params = dict(parse_qsl(url.query))
        query_params["token"] = raw_token

        return urlunsplit(
            (
                url.scheme,
                url.netloc,
                url.path,
                urlencode(query_params),
                url.fragment,
            )
        )

    # --------------------------------------------------
    # SEND VERIFICATION EMAIL
    # --------------------------------------------------

    @staticmethod
    def send_initial_verification_email(
        email: str,
        name: str | None,
        raw_token: str,
        is_resend: bool = False,
    ) -> None:

        verification_url = EmailVerificationService.build_verification_url(raw_token)

        email_service.send_verification_email(
            recipient=email,
            name=name,
            verification_url=verification_url,
            is_resend=is_resend,
        )
