
from contextlib import contextmanager
from io import BytesIO
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from src.database import SessionFactory
from src.models.document import Document as DocumentModel
from src.models.orm import Company, Document as DocumentORM, File
from src.repositories.company_repository import CompanyRepository
from src.services.file_identity import calculate_stream_hash
from src.services.ingestion import (
    DocumentIngestionResult,
    DocumentIngestionService,
    DocumentUploadError,
)


class FakeDocumentStorage:
    """Simulates Azure storage for recovery tests."""

    def __init__(self, existing_blob=None):
        self.existing_blob = existing_blob
        self.uploaded_blob_name = None
        self.uploaded_bytes = None

    def build_blob_name(
        self,
        company_id: str,
        document_id: str,
        filename: str,
    ) -> str:
        return f"{company_id}/{document_id}/{filename}"

    def exists(
        self,
        company_id: str,
        document_id: str,
        filename: str,
    ) -> bool:
        return self.existing_blob is not None

    @contextmanager
    def download_document(
        self,
        company_id: str,
        document_id: str,
        filename: str,
    ):
        yield BytesIO(self.existing_blob)

    def save_document(
        self,
        stream,
        company_id: str,
        document_id: str,
        filename: str,
        content_type=None,
    ) -> None:
        self.uploaded_blob_name = self.build_blob_name(
            company_id=company_id,
            document_id=document_id,
            filename=filename,
        )
        self.uploaded_bytes = stream.read()


def create_failed_document(content: bytes):
    """Create a company, file, and failed document in PostgreSQL."""

    company_id = None
    document_id = uuid4()
    file_id = calculate_stream_hash(BytesIO(content))
    filename = "recovery_test.pdf"

    try:
        with SessionFactory.begin() as session:
            company = CompanyRepository().create(
                session=session,
                company_name=f"Recovery Test Company {uuid4()}",
            )
            company_id = company.company_id

        document = DocumentModel(
            document_id=document_id,
            company_id=company_id,
            filename=filename,
            file_type="pdf",
            source="recovery_test",
        )

        storage = FakeDocumentStorage()

        service = DocumentIngestionService(storage=storage)

        # First create the document through the real ingestion service.
        # The fake storage is replaced below with one that fails once.
        class FailingStorage(FakeDocumentStorage):
            def save_document(self, *args, **kwargs):
                raise OSError("Simulated initial storage failure")

        service = DocumentIngestionService(storage=FailingStorage())

        with pytest.raises(DocumentUploadError):
            service.ingest_document(
                document=document,
                stream=BytesIO(content),
                content_type="application/pdf",
            )

        return company_id, document_id, file_id, filename

    except Exception:
        if company_id is not None:
            with SessionFactory.begin() as session:
                session.execute(
                    delete(DocumentORM).where(
                        DocumentORM.document_id == document_id
                    )
                )
                session.execute(
                    delete(File).where(File.file_id == file_id)
                )
                session.execute(
                    delete(Company).where(
                        Company.company_id == company_id
                    )
                )
        raise


def cleanup_records(company_id, document_id, file_id):
    """Delete only the records created by the test."""

    with SessionFactory.begin() as session:
        session.execute(
            delete(DocumentORM).where(
                DocumentORM.document_id == document_id
            )
        )
        session.execute(
            delete(File).where(File.file_id == file_id)
        )
        session.execute(
            delete(Company).where(Company.company_id == company_id)
        )


def run_recovery(content: bytes, existing_blob):
    company_id, document_id, file_id, filename = create_failed_document(
        content
    )

    try:
        storage = FakeDocumentStorage(existing_blob=existing_blob)
        service = DocumentIngestionService(storage=storage)

        document = DocumentModel(
            document_id=uuid4(),
            company_id=company_id,
            filename=filename,
            file_type="pdf",
            source="recovery_test",
        )

        result = service.ingest_document(
            document=document,
            stream=BytesIO(content),
            content_type="application/pdf",
            return_result=True,
        )

        assert isinstance(result, DocumentIngestionResult)
        assert result.recovered is True
        assert result.document.document_id == document_id
        assert result.document.file_id == file_id
        assert result.document.status == "uploaded"

        with SessionFactory() as session:
            persisted_document = session.scalars(
                select(DocumentORM).where(
                    DocumentORM.document_id == document_id
                )
            ).one()

            assert persisted_document.status == "uploaded"

        return storage

    finally:
        cleanup_records(company_id, document_id, file_id)


def test_recovery_when_existing_blob_matches_hash():
    content = b"Existing blob content for recovery."

    storage = run_recovery(
        content=content,
        existing_blob=content,
    )

    assert storage.uploaded_bytes is None


def test_recovery_when_blob_is_missing():
    content = b"Missing blob content for recovery."

    storage = run_recovery(
        content=content,
        existing_blob=None,
    )

    assert storage.uploaded_bytes == content


def test_recovery_rejects_existing_blob_with_wrong_hash():
    content = b"Original document content."
    incorrect_blob = b"Different content in storage."

    company_id, document_id, file_id, filename = create_failed_document(
        content
    )

    try:
        storage = FakeDocumentStorage(existing_blob=incorrect_blob)
        service = DocumentIngestionService(storage=storage)

        document = DocumentModel(
            document_id=uuid4(),
            company_id=company_id,
            filename=filename,
            file_type="pdf",
            source="recovery_test",
        )

        with pytest.raises(
            DocumentUploadError,
            match="SHA-256 does not match",
        ):
            service.ingest_document(
                document=document,
                stream=BytesIO(content),
                content_type="application/pdf",
                return_result=True,
            )

        assert storage.uploaded_bytes is None

        with SessionFactory() as session:
            persisted_document = session.scalars(
                select(DocumentORM).where(
                    DocumentORM.document_id == document_id
                )
            ).one()

            assert persisted_document.status == "failed"

    finally:
        cleanup_records(company_id, document_id, file_id)
