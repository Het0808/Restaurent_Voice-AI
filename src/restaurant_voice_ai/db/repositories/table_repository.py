"""Restaurant table persistence operations."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from restaurant_voice_ai.db.models.restaurant_table import RestaurantTable


class TableRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, table: RestaurantTable) -> RestaurantTable:
        self.session.add(table)
        await self.session.flush()
        return table

    async def get_by_id(self, table_id: uuid.UUID) -> RestaurantTable | None:
        return await self.session.get(RestaurantTable, table_id)

    async def get_by_number(self, table_number: int) -> RestaurantTable | None:
        result = await self.session.execute(
            select(RestaurantTable).where(RestaurantTable.table_number == table_number)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[RestaurantTable]:
        result = await self.session.scalars(
            select(RestaurantTable).order_by(RestaurantTable.table_number)
        )
        return list(result)

    async def list_active(self) -> list[RestaurantTable]:
        result = await self.session.scalars(
            select(RestaurantTable)
            .where(RestaurantTable.is_active.is_(True))
            .order_by(RestaurantTable.table_number)
        )
        return list(result)

    async def find_candidates(
        self, minimum_capacity: int, *, lock: bool = False
    ) -> list[RestaurantTable]:
        statement = (
            select(RestaurantTable)
            .where(
                RestaurantTable.is_active.is_(True),
                RestaurantTable.capacity >= minimum_capacity,
            )
            .order_by(RestaurantTable.capacity, RestaurantTable.table_number)
        )
        if lock:
            statement = statement.with_for_update()
        result = await self.session.scalars(statement)
        return list(result)
