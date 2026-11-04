from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # NVIDIA
    NVIDIA_API_KEY: str
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"

    # Groq
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str | None = None

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_ISSUER: str = "birdwing-api"
    JWT_AUDIENCE: str = "birdwing-client"

    # Authentication Cookies
    AUTH_COOKIE_NAME: str = "access_token"
    AUTH_COOKIE_HTTP_ONLY: bool = True
    AUTH_COOKIE_SECURE: bool = True
    AUTH_COOKIE_SAME_SITE: str = "lax"
    AUTH_COOKIE_PATH: str = "/"
    AUTH_COOKIE_DOMAIN: str | None = None

    # Email Configuration
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_FROM_NAME: str = "Birdwing"

    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_PORT: int = 587
    MAIL_STARTTLS: bool = True

    # Email Verification
    EMAIL_VERIFICATION_URL: str
    EMAIL_VERIFICATION_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
