"""Shared test fixtures."""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(app_env="test", cors_origins=[])


@pytest_asyncio.fixture
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client
