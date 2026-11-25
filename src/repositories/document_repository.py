from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.orm import Document


class DocumentRepository:
    async def get_by_id(
        self,
        session: AsyncSession,
        document_id: UUID,
    ) -> Document | None:
        statement = select(Document).where(Document.document_id == document_id)

        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def create(
        self,
        session: AsyncSession,
        document_id: UUID,
        company_id: UUID,
        file_id: str,
        filename: str,
        file_type: str,
        blob_name: str,
        version: int = 1,
        source: str | None = None,
        status: str = "pending",
    ) -> Document:
        document = Document(
            document_id=document_id,
            company_id=company_id,
            file_id=file_id,
            filename=filename,
            file_type=file_type,
            blob_name=blob_name,
            version=version,
            source=source,
            status=status,
        )

        session.add(document)
        await session.flush()

        return document

    async def update_status(
        self,
        session: AsyncSession,
        document_id: UUID,
        status: str,
    ) -> Document | None:
        document = await self.get_by_id(session, document_id)

        if document is None:
            return None

        document.status = status
        await session.flush()

        return document

    async def get_by_company_and_file(
        self,
        session: AsyncSession,
        company_id: UUID,
        file_id: str,
        for_update: bool = False,
    ) -> Document | None:
        statement = select(Document).where(
            Document.company_id == company_id,
            Document.file_id == file_id,
        )

        if for_update:
            statement = statement.with_for_update()

        result = await session.execute(statement)
        return result.scalar_one_or_none()
