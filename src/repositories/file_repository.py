from sqlalchemy import select

# Select is used to construct SQL SELECT statements in a more Pythonic way, allowing for easier querying of the database using SQLAlchemy's ORM capabilities.
from sqlalchemy.ext.asyncio import AsyncSession

from models.orm_legacy import File


class FileRepository:
    async def get_by_id(
        self,
        session: AsyncSession,
        file_id: str,
    ) -> File | None:
        statement = select(File).where(File.file_id == file_id)

        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def create(
        self,
        session: AsyncSession,
        file_id: str,
    ) -> File:
        file_record = File(file_id=file_id)

        session.add(file_record)
        await session.flush()

        return file_record
