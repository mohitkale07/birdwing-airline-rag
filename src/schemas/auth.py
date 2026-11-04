from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    StringConstraints,
)


def normalize_name(value: str) -> str:
    value = value.strip()

    if not value:
        raise ValueError("Name cannot be empty")

    return value


def normalize_email(value: EmailStr) -> str:
    return str(value).strip().lower()


NameStr = Annotated[
    str,
    StringConstraints(min_length=2, max_length=150),
    AfterValidator(normalize_name),
]

Email = Annotated[
    EmailStr,
    AfterValidator(normalize_email),
]

PasswordStr = Annotated[
    str,
    StringConstraints(min_length=8, max_length=128),
]

EmailVerificationTokenStr = Annotated[
    str,
    StringConstraints(min_length=1, max_length=255),
]


class RegisterRequest(BaseModel):
    name: NameStr
    email: Email
    password: PasswordStr

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Mohit",
                    "email": "mohit@example.com",
                    "password": "StrongPassword123",
                }
            ]
        }
    )


class RegisterResponse(BaseModel):
    message: str


class LoginRequest(BaseModel):
    email: Email
    password: PasswordStr

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "mohit@example.com",
                    "password": "StrongPassword123",
                }
            ]
        }
    )


class VerifyEmailRequest(BaseModel):
    token: EmailVerificationTokenStr


class ResendVerificationEmailRequest(BaseModel):
    email: Email

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"email": "mohit@example.com"}]}
    )
