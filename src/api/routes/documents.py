from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)

from src.api.dependencies import get_ingestion_service
from src.api.validators.documents import (
    validate_file_extension,
    validate_file_size,
)
from src.models.document import Document
from src.schemas.documents import DocumentUploadResponse
from src.services.ingestion import (
    CompanyNotFoundError,
    DocumentIngestionResult,
    DocumentIngestionService,
    DocumentUploadError,
    DuplicateDocumentError,
)

router = APIRouter()


@router.post(
    "/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: Annotated[UploadFile, File(...)],
    company_id: Annotated[UUID, Form()],
    ingestion_service: Annotated[
        DocumentIngestionService,
        Depends(get_ingestion_service),
    ],
) -> DocumentUploadResponse:
    """
    Upload a supported document for an existing company.

    The ingestion service coordinates metadata persistence
    and uploading the file to Azure Blob Storage.
    """

    try:
        if not file.filename or not file.filename.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A filename is required.",
            )

        validate_file_size(file)
        file_type = validate_file_extension(file.filename)

        document = Document(
            company_id=company_id,
            filename=Path(file.filename).name,
            file_type=file_type,
            source="api_upload",
        )

        try:
            uploaded_result = await ingestion_service.ingest_document(
                document=document,
                stream=file.file,
                content_type=file.content_type,
                return_result=True,
            )

        except CompanyNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The specified company does not exist.",
            ) from exc

        except DuplicateDocumentError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=("This document has already been uploaded for this company."),
            ) from exc

        except DocumentUploadError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The document could not be uploaded to storage.",
            ) from exc

        if not isinstance(uploaded_result, DocumentIngestionResult):
            raise TypeError("The ingestion service returned an unexpected result.")

        uploaded_document = uploaded_result.document

        message = (
            "A previous upload attempt failed. "
            "The document has now been recovered successfully."
            if uploaded_result.recovered
            else "Document uploaded successfully."
        )

        return DocumentUploadResponse(
            document_id=str(uploaded_document.document_id),
            filename=uploaded_document.filename,
            company_id=str(uploaded_document.company_id),
            status=uploaded_document.status,
            message=message,
        )

    finally:
        await file.close()
