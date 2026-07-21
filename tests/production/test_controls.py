"""Offline production-control unit tests."""

import asyncio
import json
import logging
from io import StringIO

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from restaurant_voice_ai.auth.api_keys import authenticate_api_key, fingerprint
from restaurant_voice_ai.auth.models import Role
from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.main import create_app
from restaurant_voice_ai.observability.logging import JsonFormatter
from restaurant_voice_ai.observability.middleware import SAFE_REQUEST_ID
from restaurant_voice_ai.observability.redaction import mask_phone_numbers, redact_url
from restaurant_voice_ai.persistence.redis.idempotency import (
    IdempotencyStatus,
    InMemoryIdempotencyStore,
)
from restaurant_voice_ai.persistence.redis.locks import InMemoryDistributedLock
from restaurant_voice_ai.rate_limit.in_memory import InMemoryRateLimiter


def test_api_key_roles_fingerprints_and_constant_time_behavior() -> None:
    clients = [SecretStr("client-secret")]
    admins = [SecretStr("admin-secret")]
    assert authenticate_api_key("client-secret", clients, admins).role is Role.CLIENT
    assert authenticate_api_key("admin-secret", clients, admins).role is Role.ADMIN
    assert authenticate_api_key("wrong", clients, admins) is None
    assert "client-secret" not in fingerprint("client-secret")


def test_production_configuration_rejects_unsafe_values() -> None:
    settings = Settings(
        _env_file=None,
        app_env="production",
        debug=True,
        cors_origins=["https://restaurant.example"],
        allowed_origins=["https://restaurant.example"],
    )
    with pytest.raises(ValueError, match="Unsafe production configuration"):
        settings.validate_runtime_configuration()


def test_request_id_auth_and_metrics_contract() -> None:
    settings = Settings(
        _env_file=None,
        app_env="test",
        cors_origins=[],
        api_auth_enabled=True,
        api_keys=[SecretStr("client-secret")],
        admin_api_keys=[SecretStr("admin-secret")],
    )
    with TestClient(create_app(settings)) as client:
        live = client.get("/health/live", headers={"X-Request-ID": "safe-demo-001"})
        assert live.status_code == 200
        assert live.headers["X-Request-ID"] == "safe-demo-001"
        generated = client.get("/health/live", headers={"X-Request-ID": "bad value"})
        assert generated.headers["X-Request-ID"] != "bad value"
        assert client.get("/metrics").status_code == 401
        assert client.get("/metrics", headers={"X-API-Key": "client-secret"}).status_code == 403
        allowed = client.get("/metrics", headers={"X-API-Key": "admin-secret"})
        assert allowed.status_code == 200
        assert "restaurant_http_requests_total" in allowed.text
        assert client.get("/health/live", headers={"Host": "attacker.invalid"}).status_code == 400
        assert "ApiKeyAuth" in client.get("/openapi.json").json()["components"]["securitySchemes"]


@pytest.mark.asyncio
async def test_rate_limit_idempotency_and_owned_lock() -> None:
    limiter = InMemoryRateLimiter()
    first = await limiter.check("client", 1, 60)
    second = await limiter.check("client", 1, 60)
    assert first.allowed and not second.allowed

    store = InMemoryIdempotencyStore()
    assert await store.reserve("safe-hash", 30)
    assert not await store.reserve("safe-hash", 30)
    await store.complete("safe-hash", {"confirmation_code": "RSV-TEST"}, 30)
    record = await store.get("safe-hash")
    assert record and record.status is IdempotencyStatus.COMPLETED

    lock = InMemoryDistributedLock()
    entered: list[int] = []

    async def worker(value: int) -> None:
        async with lock.acquire("conversation"):
            entered.append(value)
            await asyncio.sleep(0)

    await asyncio.gather(worker(1), worker(2))
    assert sorted(entered) == [1, 2]


def test_json_logging_and_redaction() -> None:
    output = StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("safe-test")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)
    logger.info("Caller phone +91 9999999999")
    payload = json.loads(output.getvalue())
    assert "9999999999" not in payload["event"]
    assert mask_phone_numbers("9999999999").endswith("9999")
    assert "password" not in redact_url("redis://user:password@localhost:6379/0")
    assert SAFE_REQUEST_ID.fullmatch("safe-demo-001")
