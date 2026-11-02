"""Application configuration loaded from environment variables."""
from functools import lru_cache
from typing import Literal
from pydantic import AnyUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_URL: str = "http://localhost:3000"
    API_URL: str = "http://localhost:8000"
    SECRET_KEY: str = "dev-secret-key-change-in-production"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./agenthub_dev.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "dev-jwt-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # OAuth (optional)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # AI Providers
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Storage
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_BUCKET: str = "agenthub"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_REGION: str = "us-east-1"

    # Payments
    PAYMENT_PROVIDER: Literal["simulator", "razorpay", "stripe"] = "simulator"
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Email
    EMAIL_PROVIDER: Literal["console", "smtp", "sendgrid"] = "console"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@agenthub.example"

    # Monitoring
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""
    ERROR_TRACKING_DSN: str = ""
    LOG_LEVEL: str = "INFO"

    @field_validator("SECRET_KEY", "JWT_SECRET_KEY")
    @classmethod
    def validate_secrets(cls, v: str) -> str:
        if len(v) < 16:
            raise ValueError("Secret key must be at least 16 characters")
        return v

    @model_validator(mode="after")
    def validate_production_requirements(self):
        if self.APP_ENV == "production":
            insecure_defaults = [
                "dev-secret-key-change-in-production",
                "change-me-minimum-32-chars-random-secret",
                "dev-jwt-secret-change-in-production",
                "change-me-jwt-secret-minimum-32-chars",
            ]
            if self.SECRET_KEY in insecure_defaults or len(self.SECRET_KEY) < 32:
                raise ValueError("SECRET_KEY must be a cryptographically secure random string of at least 32 characters in production.")
            if self.JWT_SECRET_KEY in insecure_defaults or len(self.JWT_SECRET_KEY) < 32:
                raise ValueError("JWT_SECRET_KEY must be a cryptographically secure random string of at least 32 characters in production.")
            if self.PAYMENT_PROVIDER == "simulator":
                raise ValueError("PAYMENT_PROVIDER cannot be 'simulator' in production mode.")
        return self

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
