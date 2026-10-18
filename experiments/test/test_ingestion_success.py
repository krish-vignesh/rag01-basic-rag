
from io import BytesIO
from uuid import uuid4

from sqlalchemy import delete, select

from src.database import SessionFactory
from src.models.document import Document as DocumentModel
from src.models.orm import Company, Document as DocumentORM, File
from src.repositories.company_repository import CompanyRepository
from src.services.file_identity import calculate_stream_hash
from src.services.ingestion import DocumentIngestionService


class FakeDocumentStorage:
    """Simulates successful storage without contacting Azure."""

    def __init__(self):
        self.uploaded_blob_name = None
        self.uploaded_bytes = None

    def build_blob_name(
        self,
        company_id: str,
        document_id: str,
        filename: str,
    ) -> str:
        return f"{company_id}/{document_id}/{filename}"

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


def test_successful_document_ingestion():
    storage = FakeDocumentStorage()
    company_id = None
    document_id = uuid4()

    content = (
        b"RAG01 integration test document. "
        + str(uuid4()).encode()
    )
    stream = BytesIO(content)
    file_id = calculate_stream_hash(stream)

    try:
        # 1. Create a real company record in PostgreSQL.
        with SessionFactory.begin() as session:
            company = CompanyRepository().create(
                session=session,
                company_name=f"Test Company {uuid4()}",
            )
            company_id = company.company_id

        # 2. Create the application-level document model.
        document = DocumentModel(
            document_id=document_id,
            company_id=company_id,
            filename="test_document.pdf",
            file_type="pdf",
            source="integration_test",
        )

        # 3. Use real PostgreSQL repositories and fake storage.
        service = DocumentIngestionService(
            storage=storage,
        )

        result = service.ingest_document(
            document=document,
            stream=stream,
            content_type="application/pdf",
            return_result=True,
        )

        # 4. Verify the ingestion result.
        assert result.recovered is False
        assert result.document.document_id == document_id
        assert result.document.company_id == company_id
        assert result.document.file_id == file_id
        assert result.document.status == "uploaded"

        # 5. Verify the File and Document records in PostgreSQL.
        with SessionFactory() as session:
            file_record = session.scalars(
                select(File).where(File.file_id == file_id)
            ).one_or_none()

            persisted_document = session.scalars(
                select(DocumentORM).where(
                    DocumentORM.document_id == document_id
                )
            ).one_or_none()

            assert file_record is not None
            assert persisted_document is not None
            assert persisted_document.status == "uploaded"
            assert persisted_document.blob_name == (
                storage.uploaded_blob_name
            )

        # 6. Verify that storage received the original bytes.
        assert storage.uploaded_bytes == content
        assert storage.uploaded_blob_name == (
            f"{company_id}/{document_id}/test_document.pdf"
        )

        print("PASS: company metadata persisted")
        print("PASS: file metadata persisted")
        print("PASS: document metadata persisted")
        print("PASS: final status is uploaded")
        print("PASS: storage received the original bytes")
        print("PASS: blob name uses the expected identifiers")

    finally:
        # 7. Remove only the records created by this test.
        # Delete the document before its referenced file/company.
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


if __name__ == "__main__":
    test_successful_document_ingestion()

