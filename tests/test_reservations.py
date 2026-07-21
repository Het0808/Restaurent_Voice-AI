"""SQLite-backed reservation API behavior tests.

These tests exercise portable SQLAlchemy behavior. PostgreSQL row-lock concurrency requires a
dedicated PostgreSQL test database and is intentionally not claimed by this suite.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient


def future_time(*, days: int = 2, hours: int = 0) -> datetime:
    return (datetime.now(UTC) + timedelta(days=days, hours=hours)).replace(
        minute=0, second=0, microsecond=0
    )


def reservation_payload(
    start: datetime,
    *,
    party_size: int = 2,
    end: datetime | None = None,
    name: str = "Asha Patel",
) -> dict[str, object]:
    payload: dict[str, object] = {
        "customer_name": name,
        "customer_phone": "+919876543210",
        "party_size": party_size,
        "reservation_start": start.isoformat(),
        "language": "gu",
    }
    if end is not None:
        payload["reservation_end"] = end.isoformat()
    return payload


@pytest.mark.asyncio
async def test_create_and_list_tables(client: AsyncClient) -> None:
    created = await client.post(
        "/api/v1/tables",
        json={"table_number": 10, "capacity": 4, "area": "Window"},
    )
    assert created.status_code == 201
    table_id = created.json()["id"]

    retrieved = await client.get(f"/api/v1/tables/{table_id}")
    listed = await client.get("/api/v1/tables")
    assert retrieved.status_code == 200
    assert retrieved.json()["table_number"] == 10
    assert listed.status_code == 200
    assert listed.json()["count"] == 1


@pytest.mark.asyncio
async def test_availability_prefers_smallest_suitable_table(seeded_client: AsyncClient) -> None:
    start = future_time()
    response = await seeded_client.post(
        "/api/v1/reservations/availability",
        json={
            "party_size": 3,
            "reservation_start": start.isoformat(),
            "reservation_end": (start + timedelta(hours=1)).isoformat(),
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert [table["capacity"] for table in body["tables"]] == [4, 4, 6, 8]
    assert body["tables"][0]["table_number"] == 3


@pytest.mark.asyncio
async def test_create_and_retrieve_reservation(seeded_client: AsyncClient) -> None:
    created = await seeded_client.post(
        "/api/v1/reservations", json=reservation_payload(future_time(), party_size=3)
    )
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "confirmed"
    assert body["confirmation_code"].startswith("RSV-")
    assert body["restaurant_table"]["capacity"] == 4

    by_id = await seeded_client.get(f"/api/v1/reservations/{body['id']}")
    by_code = await seeded_client.get(
        f"/api/v1/reservations/code/{body['confirmation_code'].lower()}"
    )
    listed = await seeded_client.get("/api/v1/reservations")
    assert by_id.status_code == 200
    assert by_code.status_code == 200
    assert listed.json()["count"] == 1


@pytest.mark.asyncio
async def test_overlapping_reservation_is_rejected(seeded_client: AsyncClient) -> None:
    start = future_time()
    first = await seeded_client.post(
        "/api/v1/reservations", json=reservation_payload(start, party_size=8)
    )
    second = await seeded_client.post(
        "/api/v1/reservations",
        json=reservation_payload(start + timedelta(minutes=30), party_size=8, name="Ravi Shah"),
    )
    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["code"] == "RESERVATION_CONFLICT"


@pytest.mark.asyncio
async def test_adjacent_reservations_are_allowed(seeded_client: AsyncClient) -> None:
    start = future_time()
    end = start + timedelta(hours=1)
    first = await seeded_client.post(
        "/api/v1/reservations", json=reservation_payload(start, party_size=8, end=end)
    )
    second = await seeded_client.post(
        "/api/v1/reservations",
        json=reservation_payload(end, party_size=8, end=end + timedelta(hours=1), name="Ravi Shah"),
    )
    assert first.status_code == 201
    assert second.status_code == 201


@pytest.mark.asyncio
async def test_cancelled_reservation_stops_blocking(seeded_client: AsyncClient) -> None:
    start = future_time()
    created = await seeded_client.post(
        "/api/v1/reservations", json=reservation_payload(start, party_size=8)
    )
    reservation = created.json()
    cancelled = await seeded_client.post(
        f"/api/v1/reservations/{reservation['id']}/cancel", json={}
    )
    repeated = await seeded_client.post(f"/api/v1/reservations/{reservation['id']}/cancel", json={})
    replacement = await seeded_client.post(
        "/api/v1/reservations", json=reservation_payload(start, party_size=8, name="Ravi Shah")
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["cancelled_at"] is not None
    assert repeated.status_code == 200
    assert replacement.status_code == 201


@pytest.mark.asyncio
async def test_modify_reservation(seeded_client: AsyncClient) -> None:
    created = await seeded_client.post(
        "/api/v1/reservations", json=reservation_payload(future_time(), party_size=2)
    )
    response = await seeded_client.patch(
        f"/api/v1/reservations/{created.json()['id']}",
        json={"customer_name": "Asha Shah", "party_size": 6},
    )
    assert response.status_code == 200
    assert response.json()["customer_name"] == "Asha Shah"
    assert response.json()["restaurant_table"]["capacity"] == 6


@pytest.mark.asyncio
async def test_modification_conflict(seeded_client: AsyncClient) -> None:
    start = future_time()
    blocking = await seeded_client.post(
        "/api/v1/reservations", json=reservation_payload(start, party_size=8)
    )
    movable = await seeded_client.post(
        "/api/v1/reservations",
        json=reservation_payload(start + timedelta(hours=4), party_size=2, name="Ravi Shah"),
    )
    response = await seeded_client.patch(
        f"/api/v1/reservations/{movable.json()['id']}",
        json={"party_size": 8, "reservation_start": start.isoformat()},
    )
    assert blocking.status_code == 201
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_validation_and_missing_reservation(seeded_client: AsyncClient) -> None:
    start = future_time()
    blank_name = await seeded_client.post(
        "/api/v1/reservations", json=reservation_payload(start, name="   ")
    )
    invalid_range = await seeded_client.post(
        "/api/v1/reservations/availability",
        json={
            "party_size": 2,
            "reservation_start": start.isoformat(),
            "reservation_end": (start - timedelta(minutes=1)).isoformat(),
        },
    )
    empty_update = await seeded_client.patch(f"/api/v1/reservations/{uuid.uuid4()}", json={})
    missing = await seeded_client.get(f"/api/v1/reservations/{uuid.uuid4()}")
    assert blank_name.status_code == 422
    assert invalid_range.status_code == 422
    assert empty_update.status_code == 422
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_database_health_uses_database_dependency(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/database")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
