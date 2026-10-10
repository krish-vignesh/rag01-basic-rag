from fastapi import APIRouter, File, Form, UploadFile

from src.schemas.documents import DocumentUploadResponse


router = APIRouter()


@router.post(
    "/documents",
    response_model=DocumentUploadResponse,
)
async def upload_document(
    file: UploadFile = File(...),
    company_name: str = Form(...),
):
    return DocumentUploadResponse(
        document_id="temporary-test-id",
        filename=file.filename,
        company_id="temporary-company-id",
        status="received",
    )