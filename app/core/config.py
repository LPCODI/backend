"""Environment-driven application settings."""

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Self

from pydantic import Field, SecretStr, computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class AppEnvironment(StrEnum):
    """Runtime environment names used by deployment and tests."""

    LOCAL = "local"
    TEST = "test"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Typed settings loaded from environment variables or a local .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "AI Speech Backend"
    environment: AppEnvironment = AppEnvironment.LOCAL
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    database_url: str = (
        "postgresql+psycopg://ai_speech_user:ai_speech_password@localhost:5432/ai_speech"
    )
    test_database_url: str = (
        "postgresql+psycopg://ai_speech_user:ai_speech_password@localhost:5432/ai_speech_test"
    )
    database_echo: bool = False
    database_pool_size: int = 5
    database_max_overflow: int = 10
    redis_url: str = "redis://localhost:6379/0"
    rq_queue_name: str = "ai-speech"

    jwt_secret_key: SecretStr = Field(default=SecretStr("change-me-in-env"))
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    cors_origins: Annotated[tuple[str, ...], NoDecode] = (
        "http://localhost:3000",
        "http://localhost:8081",
    )

    openai_api_key: SecretStr | None = None
    storage_backend: str = "local"
    local_storage_path: Path = Path("storage")
    max_presentation_file_size_bytes: int = 50 * 1024 * 1024

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_v1_prefix(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("api_v1_prefix must start with '/'")
        return value.rstrip("/") or "/"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str] | tuple[str, ...]) -> tuple[str, ...]:
        if isinstance(value, str):
            return tuple(origin.strip() for origin in value.split(",") if origin.strip())
        return tuple(value)

    @model_validator(mode="after")
    def validate_production_secrets(self) -> Self:
        default_secret = Settings.model_fields["jwt_secret_key"].default
        if (
            self.environment is AppEnvironment.PRODUCTION
            and isinstance(default_secret, SecretStr)
            and self.jwt_secret_key.get_secret_value() == default_secret.get_secret_value()
        ):
            raise ValueError("jwt_secret_key must be set in production")
        return self

    @computed_field
    @property
    def is_production(self) -> bool:
        return self.environment is AppEnvironment.PRODUCTION


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings for dependency injection."""

    return Settings()
