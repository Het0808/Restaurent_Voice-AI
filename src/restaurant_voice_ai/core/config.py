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
    embedding_provider: Literal["google", "openai", "local"] = "google"
    google_api_key: str | None = None
    google_embedding_model: str = "text-embedding-004"
    openai_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    local_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chroma_persist_directory: str = ".chroma"
    chroma_collection_name: str = "restaurant_knowledge"
    rag_top_k: int = Field(default=5, ge=1, le=20)
    rag_vector_weight: float = Field(default=0.6, ge=0, le=1)
    rag_bm25_weight: float = Field(default=0.4, ge=0, le=1)
    rag_score_threshold: float = Field(default=0.15, ge=0, le=1)
    rag_chunk_size: int = Field(default=800, ge=100, le=4000)
    rag_chunk_overlap: int = Field(default=120, ge=0, le=1000)

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

    @field_validator("google_api_key", "openai_api_key", mode="before")
    @classmethod
    def blank_api_key_is_none(cls, value: object) -> object:
        return None if value == "" else value

    def model_post_init(self, _: object) -> None:
        if self.rag_chunk_overlap >= self.rag_chunk_size:
            raise ValueError("RAG_CHUNK_OVERLAP must be smaller than RAG_CHUNK_SIZE")
        if self.rag_vector_weight + self.rag_bm25_weight <= 0:
            raise ValueError("At least one RAG retrieval weight must be positive")


@lru_cache
def get_settings() -> Settings:
    """Return one cached settings instance per process."""
    return Settings()
