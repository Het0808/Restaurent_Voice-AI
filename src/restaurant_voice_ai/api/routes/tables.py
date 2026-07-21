"""Restaurant table API routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from restaurant_voice_ai.db.dependencies import get_db_session
from restaurant_voice_ai.db.schemas.table import TableCreate, TableListResponse, TableResponse
from restaurant_voice_ai.db.services.table_service import TableService

router = APIRouter(prefix="/tables", tags=["Restaurant tables"])
SessionDependency = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("", response_model=TableResponse, status_code=status.HTTP_201_CREATED)
async def create_table(data: TableCreate, session: SessionDependency) -> TableResponse:
    table = await TableService(session).create(data)
    return TableResponse.model_validate(table)


@router.get("", response_model=TableListResponse)
async def list_tables(session: SessionDependency) -> TableListResponse:
    tables = await TableService(session).list_all()
    return TableListResponse(
        items=[TableResponse.model_validate(item) for item in tables], count=len(tables)
    )


@router.get("/{table_id}", response_model=TableResponse)
async def get_table(table_id: uuid.UUID, session: SessionDependency) -> TableResponse:
    table = await TableService(session).get(table_id)
    return TableResponse.model_validate(table)
