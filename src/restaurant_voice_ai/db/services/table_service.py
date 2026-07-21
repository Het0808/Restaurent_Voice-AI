"""Restaurant table business operations."""

import logging
import uuid

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from restaurant_voice_ai.core.exceptions import (
    BusinessValidationError,
    DatabaseOperationError,
    ResourceNotFoundError,
)
from restaurant_voice_ai.db.models.restaurant_table import RestaurantTable
from restaurant_voice_ai.db.repositories.table_repository import TableRepository
from restaurant_voice_ai.db.schemas.table import TableCreate

logger = logging.getLogger(__name__)


class TableService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.tables = TableRepository(session)

    async def create(self, data: TableCreate) -> RestaurantTable:
        try:
            async with self.session.begin():
                table = await self.tables.create(RestaurantTable(**data.model_dump()))
            await self.session.refresh(table)
            return table
        except IntegrityError as exc:
            logger.info("Duplicate or invalid restaurant table", exc_info=exc)
            raise BusinessValidationError("Table number already exists") from exc
        except SQLAlchemyError as exc:
            logger.exception("Database failure while creating restaurant table")
            raise DatabaseOperationError() from exc

    async def list_all(self) -> list[RestaurantTable]:
        return await self.tables.list_all()

    async def get(self, table_id: uuid.UUID) -> RestaurantTable:
        table = await self.tables.get_by_id(table_id)
        if table is None:
            raise ResourceNotFoundError("Restaurant table not found")
        return table
