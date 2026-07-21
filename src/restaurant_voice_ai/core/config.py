"""Environment-backed application configuration."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated settings with safe local-development defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Multilingual AI Restaurant Voice Receptionist"
    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_version: str = "0.1.0"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/restaurant_voice_ai"
    db_echo: bool = False
    default_reservation_duration_minutes: int = Field(default=90, ge=15, le=480)
    restaurant_timezone: str = "Asia/Kolkata"
    max_party_size: int = Field(default=20, ge=1, le=100)

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        normalized = value.rstrip("/")
        if not normalized.startswith("/") or normalized == "":
            raise ValueError("API_V1_PREFIX must start with '/' and contain a path")
        return normalized

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, origins: list[str]) -> list[str]:
        for origin in origins:
            if origin == "*" or not origin.startswith(("http://", "https://")):
                raise ValueError("CORS_ORIGINS must contain explicit HTTP(S) origins")
        return origins


@lru_cache
def get_settings() -> Settings:
    """Return one cached settings instance per process."""
    return Settings()
