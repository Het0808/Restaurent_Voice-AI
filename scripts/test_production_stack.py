"""Offline production-control smoke test."""

from fastapi.testclient import TestClient
from pydantic import SecretStr

from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.main import create_app


def main() -> None:
    settings = Settings(
        _env_file=None,
        app_env="test",
        cors_origins=[],
        api_auth_enabled=True,
        api_keys=[SecretStr("client-placeholder")],
        admin_api_keys=[SecretStr("admin-placeholder")],
    )
    with TestClient(create_app(settings)) as client:
        live = client.get("/health/live")
        assert live.status_code == 200
        unauthorized = client.get("/metrics")
        assert unauthorized.status_code == 401
        metrics = client.get("/metrics", headers={"X-API-Key": "admin-placeholder"})
        assert metrics.status_code == 200
        assert "restaurant_http_requests_total" in metrics.text
        request_id = live.headers.get("X-Request-ID")
        assert request_id
    print("Offline production controls verification passed.")


if __name__ == "__main__":
    main()
