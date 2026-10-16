
import logging
import time
from typing import BinaryIO
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from src.config.settings import settings
from src.database import SessionFactory
from src.models.document import Document as DocumentModel
from src.repositories.company_repository import CompanyRepository
from src.repositories.document_repository import DocumentRepository
from src.repositories.file_repository import FileRepository
from src.services.file_identity import calculate_stream_hash
from src.storage.storage import DocumentStorage


logger = logging.getLogger(__name__)


class CompanyNotFoundError(Exception):
    """Raised when the requested company does not exist."""


class DuplicateDocumentError(Exception):
    """Raised when a company already has identical file content."""


class DocumentUploadError(Exception):
    """Raised when uploading a document fails."""


class DocumentIngestionService:
    """
    Coordinates document metadata persistence and Azure Blob upload.

    Responsibilities:
    - Validate company existence.
    - Identify file content using SHA-256.
    - Reject same-company duplicate content.
    - Persist file and document metadata in PostgreSQL.
    - Upload the original file to Azure Blob Storage.
    - Update the document lifecycle status.

    Chunking, embedding, and indexing belong to the separate RAG
    ingestion pipeline and are not performed by this service.
    """

    def __init__(
        self,
        session_factory=SessionFactory,
        company_repository=None,
        file_repository=None,
        document_repository=None,
        storage=None,
    ):
        self.session_factory = session_factory

        self.company_repository = (
            company_repository
            if company_repository is not None
            else CompanyRepository()
        )

        self.file_repository = (
            file_repository
            if file_repository is not None
            else FileRepository()
        )

        self.document_repository = (
            document_repository
            if document_repository is not None
            else DocumentRepository()
        )

        self.storage = (
            storage
            if storage is not None
            else DocumentStorage(
                storage_account_url=settings.azure_storage_account_url,
                container_name=settings.azure_storage_container_name,
            )
        )

    def validate_upload(
        self,
        company_id: UUID,
        stream: BinaryIO,
    ) -> str:
        """
        Validate the company and reject duplicate content.

        Returns the SHA-256 hash without changing the stream's
        original reading position.
        """

        with self.session_factory() as session:
            company = self.company_repository.get_by_id(
                session=session,
                company_id=company_id,
            )

            if company is None:
                logger.warning(
                    "Upload validation rejected: company does not exist. "
                    "company_id=%s",
                    company_id,
                )
                raise CompanyNotFoundError(
                    f"Company '{company_id}' does not exist."
                )

            hashing_started_at = time.perf_counter()

            try:
                file_id = calculate_stream_hash(stream)
            except Exception:
                logger.exception(
                    "File hashing failed during upload validation. "
                    "company_id=%s",
                    company_id,
                )
                raise

            hashing_duration = time.perf_counter() - hashing_started_at

            logger.info(
                "Document file hashing completed in %.3f seconds",
                hashing_duration,
            )

            existing_document = (
                self.document_repository.get_by_company_and_file(
                    session=session,
                    company_id=company_id,
                    file_id=file_id,
                )
            )

            if existing_document is not None:
                logger.warning(
                    "Upload validation rejected duplicate content. "
                    "company_id=%s",
                    company_id,
                )
                raise DuplicateDocumentError(
                    "This company has already uploaded "
                    "a document with identical content."
                )

            return file_id

    def ingest_document(
        self,
        document: DocumentModel,
        stream: BinaryIO,
        content_type: str | None = None,
    ):
        """
        Persist metadata, upload the original file, and update status.

        Returns the persisted document ORM object after successful
        upload and status update.
        """

        company_id = document.company_id
        document_id = document.document_id
        filename = document.filename

        # Step 1: Calculate file identity.
        hashing_started_at = time.perf_counter()

        try:
            file_id = calculate_stream_hash(stream)
        except Exception:
            logger.exception(
                "Document file hashing failed. "
                "company_id=%s document_id=%s",
                company_id,
                document_id,
            )
            raise

        hashing_duration = time.perf_counter() - hashing_started_at

        logger.info(
            "Document file hashing completed in %.3f seconds",
            hashing_duration,
        )

        # Step 2: Build the canonical Azure blob name.
        try:
            blob_name = self.storage.build_blob_name(
                company_id=str(company_id),
                document_id=str(document_id),
                filename=filename,
            )
        except Exception:
            logger.exception(
                "Failed to build Azure blob name. "
                "company_id=%s document_id=%s",
                company_id,
                document_id,
            )
            raise

        # Step 3: Persist metadata in a PostgreSQL transaction.
        metadata_started_at = time.perf_counter()

        try:
            with self.session_factory.begin() as session:
                company = self.company_repository.get_by_id(
                    session=session,
                    company_id=company_id,
                )

                if company is None:
                    logger.warning(
                        "Document upload rejected: company does not exist. "
                        "company_id=%s document_id=%s",
                        company_id,
                        document_id,
                    )
                    raise CompanyNotFoundError(
                        f"Company '{company_id}' does not exist."
                    )

                existing_document = (
                    self.document_repository.get_by_company_and_file(
                        session=session,
                        company_id=company_id,
                        file_id=file_id,
                    )
                )

                if existing_document is not None:
                    logger.warning(
                        "Document upload rejected: duplicate content. "
                        "company_id=%s document_id=%s",
                        company_id,
                        document_id,
                    )
                    raise DuplicateDocumentError(
                        "This company has already uploaded "
                        "a document with identical content."
                    )

                # File identity is global. Identical bytes can share
                # a File record across different companies.
                file_record = self.file_repository.get_by_id(
                    session=session,
                    file_id=file_id,
                )

                if file_record is None:
                    self.file_repository.create(
                        session=session,
                        file_id=file_id,
                    )

                # Create the company-owned document record.
                self.document_repository.create(
                    session=session,
                    document_id=document_id,
                    company_id=company_id,
                    file_id=file_id,
                    filename=filename,
                    file_type=document.file_type,
                    blob_name=blob_name,
                    version=document.version,
                    source=document.source,
                    status="pending",
                )

            # The transaction has committed successfully.
            metadata_duration = (
                time.perf_counter() - metadata_started_at
            )

            logger.info(
                "PostgreSQL metadata transaction completed in "
                "%.3f seconds. document_id=%s",
                metadata_duration,
                document_id,
            )

        except CompanyNotFoundError:
            raise

        except DuplicateDocumentError:
            raise

        except IntegrityError as exc:
            # Handle a concurrent request that inserted a duplicate
            # after our initial duplicate check.
            try:
                with self.session_factory() as session:
                    duplicate = (
                        self.document_repository.get_by_company_and_file(
                            session=session,
                            company_id=company_id,
                            file_id=file_id,
                        )
                    )
            except Exception:
                logger.exception(
                    "Failed to check for a duplicate after a database "
                    "integrity error. company_id=%s document_id=%s",
                    company_id,
                    document_id,
                )
                raise

            if duplicate is not None:
                logger.warning(
                    "Concurrent duplicate upload rejected. "
                    "company_id=%s document_id=%s",
                    company_id,
                    document_id,
                )
                raise DuplicateDocumentError(
                    "This company has already uploaded "
                    "a document with identical content."
                ) from exc

            logger.exception(
                "PostgreSQL integrity error during metadata persistence. "
                "company_id=%s document_id=%s",
                company_id,
                document_id,
            )
            raise

        except Exception:
            logger.exception(
                "PostgreSQL metadata transaction failed. "
                "company_id=%s document_id=%s",
                company_id,
                document_id,
            )
            raise

        # Step 4: Upload the original stream to Azure.
        azure_upload_started_at = time.perf_counter()

        try:
            stream.seek(0)

            self.storage.save_document(
                stream=stream,
                company_id=str(company_id),
                document_id=str(document_id),
                filename=filename,
                content_type=content_type,
            )

        except Exception as upload_error:
            logger.exception(
                "Azure Blob upload failed. "
                "company_id=%s document_id=%s",
                company_id,
                document_id,
            )

            # Step 5: Record the failure in a new transaction.
            try:
                with self.session_factory.begin() as session:
                    failed_document = (
                        self.document_repository.update_status(
                            session=session,
                            document_id=document_id,
                            status="failed",
                        )
                    )

                    if failed_document is None:
                        raise RuntimeError(
                            "The document record could not be found "
                            "while recording the failed upload."
                        )

            except Exception as status_error:
                logger.exception(
                    "Azure upload failed and PostgreSQL could not "
                    "record the failed status. "
                    "company_id=%s document_id=%s",
                    company_id,
                    document_id,
                )

                raise DocumentUploadError(
                    "Azure upload failed, and the document status "
                    "could not be updated to 'failed'."
                ) from status_error

            raise DocumentUploadError(
                "The document metadata was saved, but the Azure "
                "Blob upload failed. The document status is 'failed'."
            ) from upload_error

        azure_upload_duration = (
            time.perf_counter() - azure_upload_started_at
        )

        logger.info(
            "Azure Blob upload completed in %.3f seconds. "
            "company_id=%s document_id=%s",
            azure_upload_duration,
            company_id,
            document_id,
        )

        # Step 6: Mark the document as uploaded.
        status_update_started_at = time.perf_counter()

        try:
            with self.session_factory.begin() as session:
                updated_document = (
                    self.document_repository.update_status(
                        session=session,
                        document_id=document_id,
                        status="uploaded",
                    )
                )

                if updated_document is None:
                    raise RuntimeError(
                        "The document record disappeared after "
                        "the Azure upload succeeded."
                    )

            status_update_duration = (
                time.perf_counter() - status_update_started_at
            )

            logger.info(
                "PostgreSQL status update completed in %.3f seconds. "
                "document_id=%s status=uploaded",
                status_update_duration,
                document_id,
            )

        except Exception as status_error:
            logger.exception(
                "Azure upload succeeded, but the PostgreSQL status "
                "update failed. company_id=%s document_id=%s",
                company_id,
                document_id,
            )

            # Do not delete the blob automatically. Azure and
            # PostgreSQL do not share an atomic transaction.
            raise DocumentUploadError(
                "The Azure upload succeeded, but the PostgreSQL "
                "status update failed. The blob may exist while "
                "the database status remains 'pending'."
            ) from status_error

        return updated_document
