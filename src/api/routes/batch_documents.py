

import logging
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from src.api.validators.batch_doc_rules import validate_batch_upload
from src.api.validators.documents import validate_file_extension
from src.models.document import Document
from src.schemas.documents import (
    BatchDocumentUploadResponse,
    BatchDocumentUploadResult,
    DocumentUploadResponse,
)
from src.services.ingestion import (
    CompanyNotFoundError,
    DocumentIngestionResult,
    DocumentIngestionService,
    DocumentUploadError,
    DuplicateDocumentError,
)


logger = logging.getLogger(__name__)

router = APIRouter()
ingestion_service = DocumentIngestionService()


@router.post(
    "/documents/batch",
    response_model=BatchDocumentUploadResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_documents_batch(
    files: Annotated[list[UploadFile], File(...)],
    company_id: Annotated[UUID, Form()],
) -> BatchDocumentUploadResponse:
    """Upload multiple documents for an existing company."""

    try:
        # Phase 1: Validate the complete batch before ingestion.
        validate_batch_upload(files)

        prepared_files: list[tuple[UploadFile, str, str]] = []

        for file in files:
            if not file.filename or not file.filename.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Every file must have a filename.",
                )

            filename = Path(file.filename).name
            file_type = validate_file_extension(filename)

            prepared_files.append((file, filename, file_type))

        logger.info(
            "Batch document upload started. company_id=%s file_count=%s",
            company_id,
            len(prepared_files),
        )

        # Phase 2: Process files sequentially.
        results: list[BatchDocumentUploadResult] = []
        stop_reason: str | None = None

        for file, filename, file_type in prepared_files:
            document = Document(
                company_id=company_id,
                filename=filename,
                file_type=file_type,
                source="api_upload",
            )

            try:
                # Run synchronous database, hashing, and Azure work
                # outside the asynchronous event-loop thread.
                uploaded_result = await run_in_threadpool(
                    ingestion_service.ingest_document,
                    document=document,
                    stream=file.file,
                    content_type=file.content_type,
                    return_result=True,
                )

                if not isinstance(
                    uploaded_result,
                    DocumentIngestionResult,
                ):
                    raise RuntimeError(
                        "The ingestion service returned an unexpected result."
                    )

                uploaded_document = uploaded_result.document

                message = (
                    "A previous upload attempt failed. "
                    "The document has now been recovered successfully."
                    if uploaded_result.recovered
                    else "Document uploaded successfully."
                )

                results.append(
                    BatchDocumentUploadResult(
                        filename=filename,
                        outcome="success",
                        document=DocumentUploadResponse(
                            document_id=str(uploaded_document.document_id),
                            filename=uploaded_document.filename,
                            company_id=str(uploaded_document.company_id),
                            status=uploaded_document.status,
                            message=message,
                        ),
                    )
                )

            except DuplicateDocumentError:
                # A duplicate is a file-specific failure.
                # Continue processing the remaining files.
                results.append(
                    BatchDocumentUploadResult(
                        filename=filename,
                        outcome="failure",
                        error_code="duplicate_document",
                        message=(
                            "This document has already been uploaded "
                            "for this company."
                        ),
                    )
                )
                continue

            except CompanyNotFoundError:
                # The company is shared by every file in the batch.
                if not results:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="The specified company does not exist.",
                    )

                results.append(
                    BatchDocumentUploadResult(
                        filename=filename,
                        outcome="failure",
                        error_code="company_not_found",
                        message=(
                            "The company could not be found. "
                            "The remaining files were not processed."
                        ),
                    )
                )
                stop_reason = "company_not_found"
                break

            except DocumentUploadError:
                # Database or Azure state may be uncertain.
                # Stop rather than blindly processing more files.
                logger.warning(
                    "Batch processing stopped after an ingestion failure. "
                    "company_id=%s filename=%s",
                    company_id,
                    filename,
                )

                results.append(
                    BatchDocumentUploadResult(
                        filename=filename,
                        outcome="failure",
                        error_code="document_upload_failed",
                        message=(
                            f"We couldn't complete the upload of "
                            f"{filename}. Please try again later."
                        ),
                    )
                )
                stop_reason = "document_upload_failed"
                break

            except Exception:
                # Keep technical details in server logs only.
                logger.exception(
                    "Unexpected batch ingestion error. "
                    "company_id=%s filename=%s",
                    company_id,
                    filename,
                )

                results.append(
                    BatchDocumentUploadResult(
                        filename=filename,
                        outcome="failure",
                        error_code="internal_error",
                        message=(
                            f"We couldn't complete the upload of "
                            f"{filename}. Please contact support "
                            "if the problem continues."
                        ),
                    )
                )
                stop_reason = "internal_error"
                break

        # Phase 3: Report files that were never attempted.
        processed_count = len(results)

        if stop_reason is not None:
            for _, filename, _ in prepared_files[processed_count:]:
                results.append(
                    BatchDocumentUploadResult(
                        filename=filename,
                        outcome="not_processed",
                        error_code="batch_stopped",
                        message=(
                            "This file wasn't processed because an "
                            "earlier file encountered an error. "
                            "Please submit it again after resolving "
                            "the earlier failure."
                        ),
                    )
                )

        # Phase 4: Calculate summary counts from individual outcomes.
        successful_uploads = sum(
            result.outcome == "success" for result in results
        )
        failed_uploads = sum(
            result.outcome == "failure" for result in results
        )
        not_processed = sum(
            result.outcome == "not_processed" for result in results
        )

        response = BatchDocumentUploadResponse(
            total_files=len(prepared_files),
            successful_uploads=successful_uploads,
            failed_uploads=failed_uploads,
            not_processed=not_processed,
            results=results,
        )

        logger.info(
            "Batch document upload completed. "
            "company_id=%s total=%s successful=%s failed=%s "
            "not_processed=%s stop_reason=%s",
            company_id,
            response.total_files,
            response.successful_uploads,
            response.failed_uploads,
            response.not_processed,
            stop_reason or "none",
        )

        return response

    finally:
        # Close every uploaded file, including on validation failures.
        for file in files:
            await file.close()
