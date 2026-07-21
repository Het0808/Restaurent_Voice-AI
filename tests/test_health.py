"""Tests for foundational service endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root(client: AsyncClient) -> None:
    response = await client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Multilingual AI Restaurant Voice Receptionist API",
        "docs": "/docs",
        "health": "/health",
    }


@pytest.mark.asyncio
async def test_unversioned_health(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "Multilingual AI Restaurant Voice Receptionist",
        "version": "0.1.0",
        "environment": "test",
    }


@pytest.mark.asyncio
async def test_versioned_health_matches_contract(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    body = response.json()

    assert response.status_code == 200
    assert set(body) == {"status", "service", "version", "environment"}
    assert body["status"] == "healthy"
    assert body["service"] == "Multilingual AI Restaurant Voice Receptionist"
    assert body["version"] == "0.1.0"
    assert body["environment"] == "test"
