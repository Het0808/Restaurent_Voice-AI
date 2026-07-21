"""Environment-backed application configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
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
    app_version: str = "0.8.0"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["text", "json"] = "text"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/restaurant_voice_ai"
    db_echo: bool = False
    default_reservation_duration_minutes: int = Field(default=90, ge=15, le=480)
    restaurant_timezone: str = "Asia/Kolkata"
    max_party_size: int = Field(default=20, ge=1, le=100)
    embedding_provider: Literal["google", "openai", "local"] = "google"
    google_api_key: str | None = None
    gemini_api_key: str | None = None
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
    conversation_intent_provider: Literal["rules", "google"] = "rules"
    google_chat_model: str | None = None
    gemini_model: str | None = None
    conversation_mode: Literal["rules", "google", "hybrid"] = "hybrid"
    conversation_entity_provider: Literal["rules", "google"] = "google"
    conversation_response_provider: Literal["rules", "google"] = "google"
    conversation_memory_backend: Literal["memory", "redis"] = "memory"
    conversation_max_history_messages: int = Field(default=20, ge=2, le=100)
    conversation_max_tool_iterations: int = Field(default=3, ge=1, le=10)
    conversation_require_mutation_confirmation: bool = True
    conversation_memory_ttl_seconds: int = Field(default=3600, ge=30, le=86400)
    voice_enabled: bool = True
    voice_stt_provider: Literal["fake", "google_cloud", "gemini_live"] = "fake"
    voice_tts_provider: Literal["fake", "google_cloud", "gemini_live"] = "fake"
    voice_vad_provider: Literal["energy"] = "energy"
    voice_input_format: Literal["pcm_s16le", "webm"] = "pcm_s16le"
    voice_input_sample_rate: int = Field(default=16000, ge=8000, le=48000)
    voice_input_channels: Literal[1] = 1
    voice_output_format: Literal["pcm_s16le"] = "pcm_s16le"
    voice_output_sample_rate: int = Field(default=24000, ge=8000, le=48000)
    voice_output_channels: Literal[1] = 1
    voice_frame_duration_ms: int = Field(default=20, ge=10, le=100)
    voice_max_frame_bytes: int = Field(default=65536, ge=320, le=1048576)
    voice_max_utterance_seconds: int = Field(default=30, ge=1, le=120)
    voice_max_session_seconds: int = Field(default=1800, ge=30, le=7200)
    voice_session_idle_timeout_seconds: int = Field(default=120, ge=5, le=1800)
    voice_end_silence_ms: int = Field(default=700, ge=100, le=3000)
    voice_min_speech_ms: int = Field(default=200, ge=20, le=2000)
    voice_pre_speech_buffer_ms: int = Field(default=300, ge=0, le=2000)
    voice_energy_threshold: int = Field(default=500, ge=1, le=32767)
    voice_tts_chunk_bytes: int = Field(default=4096, ge=256, le=65536)
    voice_max_transcript_chars: int = Field(default=2000, ge=1, le=10000)
    voice_allow_partial_transcripts: bool = True
    voice_allow_barge_in: bool = True
    voice_supported_languages: list[str] = Field(
        default_factory=lambda: ["en-IN", "hi-IN", "gu-IN"]
    )
    voice_default_language: str = "en-IN"
    voice_allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:8000", "http://127.0.0.1:8000"]
    )
    voice_max_json_bytes: int = Field(default=16384, ge=256, le=65536)
    voice_max_sessions: int = Field(default=100, ge=1, le=10000)
    voice_max_pending_frames: int = Field(default=100, ge=1, le=1000)
    voice_stt_timeout_seconds: float = Field(default=15, gt=0, le=60)
    voice_conversation_timeout_seconds: float = Field(default=30, gt=0, le=120)
    voice_tts_timeout_seconds: float = Field(default=15, gt=0, le=60)
    google_cloud_project: str | None = None
    google_cloud_stt_location: str = "global"
    google_cloud_stt_recognizer: str | None = None
    google_cloud_stt_model: str = "latest_short"
    google_cloud_tts_voice: str | None = None
    api_auth_enabled: bool = False
    api_key_header_name: str = "X-API-Key"
    api_keys: list[SecretStr] = Field(default_factory=list)
    admin_api_keys: list[SecretStr] = Field(default_factory=list)
    public_health_endpoints: bool = True
    websocket_query_api_key_enabled: bool = False
    request_id_header: str = "X-Request-ID"
    trusted_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "testserver"]
    )
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:8000", "http://127.0.0.1:8000"]
    )
    trust_proxy_headers: bool = False
    redis_enabled: bool = False
    redis_url: SecretStr = SecretStr("redis://localhost:6379/0")
    redis_prefix: str = "restaurant_voice_ai"
    redis_connect_timeout_seconds: float = Field(default=3, gt=0, le=30)
    redis_socket_timeout_seconds: float = Field(default=3, gt=0, le=30)
    redis_max_connections: int = Field(default=20, ge=1, le=500)
    idempotency_backend: Literal["memory", "redis"] = "memory"
    rate_limit_backend: Literal["memory", "redis"] = "memory"
    conversation_history_enabled: bool = True
    conversation_history_retention_days: int = Field(default=30, ge=1, le=3650)
    conversation_history_store_raw_audio: bool = False
    conversation_history_store_transcripts: bool = True
    conversation_history_store_phone_masked: bool = True
    rate_limit_enabled: bool = True
    rate_limit_text_requests_per_minute: int = Field(default=60, ge=1, le=10000)
    rate_limit_voice_connections_per_minute: int = Field(default=10, ge=1, le=1000)
    rate_limit_health_requests_per_minute: int = Field(default=120, ge=1, le=10000)
    rate_limit_burst_multiplier: float = Field(default=2, ge=1, le=10)
    metrics_enabled: bool = True
    metrics_path: str = "/metrics"
    metrics_include_route_labels: bool = True
    metrics_public: bool = False
    liveness_path: str = "/health/live"
    readiness_path: str = "/health/ready"
    health_path: str = "/health"
    shutdown_grace_seconds: int = Field(default=15, ge=1, le=120)
    startup_database_timeout_seconds: int = Field(default=30, ge=1, le=120)
    startup_redis_timeout_seconds: int = Field(default=10, ge=1, le=60)
    production_allow_fake_voice: bool = False
    public_base_url: str | None = None
    twilio_account_sid: str | None = None
    twilio_auth_token: SecretStr | None = None
    twilio_phone_number: str | None = None
    twilio_staff_phone_number: str | None = None
    twilio_validate_signatures: bool = True
    twilio_voice_name: str = "Polly.Aditi"
    twilio_voice_language: str = "en-IN"
    twilio_speech_timeout: str = "auto"
    twilio_max_speech_seconds: int = Field(default=20, ge=1, le=60)
    twilio_max_retries: int = Field(default=3, ge=1, le=5)
    twilio_min_speech_confidence: float = Field(default=0.45, ge=0, le=1)
    twilio_webhook_max_chars: int = Field(default=4000, ge=100, le=10000)

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

    @field_validator(
        "google_api_key",
        "gemini_api_key",
        "openai_api_key",
        "google_chat_model",
        "gemini_model",
        mode="before",
    )
    @classmethod
    def blank_api_key_is_none(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("chroma_persist_directory", mode="after")
    @classmethod
    def resolve_chroma_directory(cls, value: str) -> str:
        path = Path(value).expanduser()
        if not path.is_absolute():
            project_root = Path(__file__).resolve().parents[3]
            path = project_root / path
        return str(path.resolve())

    def model_post_init(self, _: object) -> None:
        self.google_api_key = self.google_api_key or self.gemini_api_key
        self.google_chat_model = self.google_chat_model or self.gemini_model
        if self.rag_chunk_overlap >= self.rag_chunk_size:
            raise ValueError("RAG_CHUNK_OVERLAP must be smaller than RAG_CHUNK_SIZE")
        if self.rag_vector_weight + self.rag_bm25_weight <= 0:
            raise ValueError("At least one RAG retrieval weight must be positive")
        if self.voice_input_sample_rate * self.voice_frame_duration_ms % 1000:
            raise ValueError("Voice frame duration must produce a whole number of samples")
        if self.voice_default_language not in self.voice_supported_languages:
            raise ValueError("VOICE_DEFAULT_LANGUAGE must be supported")

    def validate_runtime_configuration(self) -> None:
        """Fail fast when production infrastructure or security is unsafe."""
        errors: list[str] = []
        redis_required = any(
            backend == "redis"
            for backend in (
                self.conversation_memory_backend,
                self.idempotency_backend,
                self.rate_limit_backend,
            )
        )
        if redis_required and not self.redis_enabled:
            errors.append("Redis must be enabled for selected backends")
        if self.app_env != "production":
            if errors:
                raise ValueError("Invalid runtime configuration: " + "; ".join(errors))
            return
        if self.debug:
            errors.append("DEBUG must be false")
        if self.log_format != "json":
            errors.append("LOG_FORMAT must be json")
        if not self.api_auth_enabled or not self.api_keys or not self.admin_api_keys:
            errors.append("client and admin API keys are required")
        if "*" in self.allowed_origins or "*" in self.cors_origins:
            errors.append("wildcard origins are forbidden")
        if "*" in self.trusted_hosts or not self.trusted_hosts:
            errors.append("explicit trusted hosts are required")
        if self.database_url.startswith("sqlite"):
            errors.append("PostgreSQL is required")
        if not self.production_allow_fake_voice and (
            self.voice_stt_provider == "fake" or self.voice_tts_provider == "fake"
        ):
            errors.append("fake voice providers are forbidden")
        if self.websocket_query_api_key_enabled:
            errors.append("WebSocket query API keys are forbidden")
        if self.conversation_history_store_raw_audio:
            errors.append("raw audio history is forbidden")
        if not self.public_base_url or not self.public_base_url.startswith("https://"):
            errors.append("PUBLIC_BASE_URL must be an HTTPS URL")
        if not self.twilio_auth_token or not self.twilio_validate_signatures:
            errors.append("Twilio signature validation and auth token are required")
        if errors:
            raise ValueError("Unsafe production configuration: " + "; ".join(errors))

    @property
    def embedding_model_name(self) -> str:
        models = {
            "google": self.google_embedding_model,
            "openai": self.openai_embedding_model,
            "local": self.local_embedding_model,
        }
        return models[self.embedding_provider]


@lru_cache
def get_settings() -> Settings:
    """Return one cached settings instance per process."""
    return Settings()
