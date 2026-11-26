
from collections.abc import AsyncGenerator
from typing import cast

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import AsyncSessionFactory
from src.services.ingestion import DocumentIngestionService


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        yield session


def get_ingestion_service(
    request: Request,
) -> DocumentIngestionService:
    return cast(
        DocumentIngestionService,
        request.app.state.ingestion_service,
    )
