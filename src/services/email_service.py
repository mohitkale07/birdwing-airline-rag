import logging
import smtplib

from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from ssl import create_default_context

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:

    def __init__(self):
        template_directory = Path(__file__).resolve().parent.parent / "templates"

        self.template_environment = Environment(
            loader=FileSystemLoader(template_directory),
            autoescape=select_autoescape(
                enabled_extensions=("html", "xml"),
            ),
        )

    def send_email(
        self,
        recipient: str,
        subject: str,
        html_content: str,
        text_content: str,
    ) -> None:

        message = EmailMessage()

        message["Subject"] = subject
        message["From"] = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM}>"
        message["To"] = recipient

        message.set_content(text_content)

        message.add_alternative(
            html_content,
            subtype="html",
        )

        context = create_default_context()

        with smtplib.SMTP(
            settings.MAIL_SERVER,
            settings.MAIL_PORT,
            timeout=20,
        ) as smtp:

            smtp.ehlo()

            if settings.MAIL_STARTTLS:
                smtp.starttls(context=context)
                smtp.ehlo()

            smtp.login(
                settings.MAIL_USERNAME,
                settings.MAIL_PASSWORD,
            )

            smtp.send_message(message)

        logger.info("Email sent successfully to %s", recipient)

    def send_verification_email(
        self,
        recipient: str,
        name: str | None,
        verification_url: str,
        is_resend: bool = False,
    ) -> None:

        template = self.template_environment.get_template(
            "emails/email_verification.html"
        )

        html_content = template.render(
            name=name or "there",
            app_name=settings.MAIL_FROM_NAME,
            verification_url=verification_url,
            expiry_minutes=settings.EMAIL_VERIFICATION_EXPIRE_MINUTES,
            is_resend=is_resend,
            year=datetime.now().year,
        )

        text_content = (
            f"Hello {name or 'there'},\n\n"
            f"Please verify your email address:\n"
            f"{verification_url}\n\n"
            f"This link expires in "
            f"{settings.EMAIL_VERIFICATION_EXPIRE_MINUTES} minutes."
        )

        self.send_email(
            recipient=recipient,
            subject="Verify your email address",
            html_content=html_content,
            text_content=text_content,
        )


email_service = EmailService()
