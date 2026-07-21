"""Shared test fixtures."""

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.db.base import Base
from restaurant_voice_ai.db.dependencies import get_db_session
from restaurant_voice_ai.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        app_env="test",
        cors_origins=[],
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        chroma_persist_directory=str(tmp_path / "chroma"),
    )


@pytest_asyncio.fixture
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    app = create_app(settings)

    async def test_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = test_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client
    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_client(client: AsyncClient) -> AsyncClient:
    for table_number, capacity in ((1, 2), (2, 2), (3, 4), (4, 4), (5, 6), (6, 8)):
        response = await client.post(
            "/api/v1/tables", json={"table_number": table_number, "capacity": capacity}
        )
        assert response.status_code == 201
    return client
