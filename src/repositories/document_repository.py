
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.orm import Document


class DocumentRepository:
    def get_by_id(
        self,
        session: Session,
        document_id: UUID,
    ) -> Document | None:
        statement = select(Document).where(
            Document.document_id == document_id
        )

        return session.scalars(statement).one_or_none()

    def create(
        self,
        session: Session,
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
        session.flush()

        return document

    def update_status(
        self,
        session: Session,
        document_id: UUID,
        status: str,
    ) -> Document | None:
        document = self.get_by_id(session, document_id)

        if document is None:
            return None

        document.status = status
        session.flush()

        return document
    
    def get_by_company_and_file(
        self,
        session: Session,
        company_id: UUID,
        file_id: str,
    ) -> Document | None:
        statement = select(Document).where(
            Document.company_id == company_id,
            Document.file_id == file_id,
        )
        return session.scalars(statement).one_or_none()


