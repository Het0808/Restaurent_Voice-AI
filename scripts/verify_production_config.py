"""Safely verify production invariants without printing secrets."""

from pydantic import SecretStr

from restaurant_voice_ai.core.config import Settings


def main() -> None:
    settings = Settings(
        _env_file=None,
        app_env="production",
        debug=False,
        log_format="json",
        api_auth_enabled=True,
        api_keys=[SecretStr("production-client-placeholder")],
        admin_api_keys=[SecretStr("production-admin-placeholder")],
        allowed_origins=["https://restaurant.example"],
        cors_origins=["https://restaurant.example"],
        trusted_hosts=["restaurant.example"],
        database_url="postgresql+asyncpg://user:password@database/restaurant",
        redis_enabled=True,
        conversation_memory_backend="redis",
        idempotency_backend="redis",
        rate_limit_backend="redis",
        voice_stt_provider="google_cloud",
        voice_tts_provider="google_cloud",
    )
    settings.validate_runtime_configuration()
    print("Production configuration validation passed.")


if __name__ == "__main__":
    main()
