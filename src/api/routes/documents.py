
from pathlib import Path
from uuid import UUID
from typing import Annotated
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from src.models.document import Document

from src.schemas.documents import DocumentUploadResponse
from src.services.ingestion import (
    CompanyNotFoundError,
    DocumentIngestionService,
    DocumentUploadError,
    DuplicateDocumentError,
)


router = APIRouter()

ingestion_service = DocumentIngestionService()

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".csv",
    ".md",
    ".txt",
    ".json",
}


def validate_file_extension(filename: str) -> str:
    """Validate the filename extension and return the normalized file type."""
    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file format.",
        )

    return extension.lstrip(".")


@router.post(
    "/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: Annotated[UploadFile, File(...)],
    company_id: Annotated[UUID, Form()],
):
    """
    Upload a supported document for an existing company.

    The ingestion service coordinates metadata persistence
    and uploading the file to Azure Blob Storage.
    """

    if not file.filename or not file.filename.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A filename is required.",
        )

    file_type = validate_file_extension(file.filename)
    document = Document(
        company_id=company_id,  # ✅ Read from validated request metadata
        filename=Path(file.filename).name,
        file_type=file_type,
        source="api_upload",
    )

    try:
        uploaded_document = ingestion_service.ingest_document(
            document=document,
            stream=file.file,
            content_type=file.content_type,
        )

    except CompanyNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The specified company does not exist.",
        ) from exc

    except DuplicateDocumentError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This document has already been uploaded for this company.",
        ) from exc

    except DocumentUploadError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The document could not be uploaded to storage.",
        ) from exc

    finally:
        await file.close()

    return DocumentUploadResponse(
        document_id=str(uploaded_document.document_id),
        filename=uploaded_document.filename,
        company_id=str(uploaded_document.company_id),
        status=uploaded_document.status,
    )
