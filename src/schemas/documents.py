
from pydantic import BaseModel, ConfigDict


class DocumentUploadResponse(BaseModel):
    """
    Public response returned after a document upload succeeds.
    """

    model_config = ConfigDict(extra="forbid")

    document_id: str
    filename: str
    company_id: str
    status: str
