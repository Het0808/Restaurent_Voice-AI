"""Idempotently seed a practical restaurant table layout."""

import asyncio

from restaurant_voice_ai.db.models.restaurant_table import RestaurantTable
from restaurant_voice_ai.db.repositories.table_repository import TableRepository
from restaurant_voice_ai.db.session import async_session_factory, dispose_engine

TABLES = ((1, 2), (2, 2), (3, 4), (4, 4), (5, 6), (6, 8))


async def seed() -> None:
    async with async_session_factory() as session, session.begin():
        repository = TableRepository(session)
        for table_number, capacity in TABLES:
            if await repository.get_by_number(table_number) is None:
                await repository.create(
                    RestaurantTable(table_number=table_number, capacity=capacity, is_active=True)
                )


async def main() -> None:
    try:
        await seed()
        print("Restaurant tables seeded successfully.")
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
