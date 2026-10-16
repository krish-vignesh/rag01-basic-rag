
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentUploadRequest(BaseModel):
    """
    Validated metadata for a document upload request.

    The uploaded file itself is received separately by FastAPI
    through multipart/form-data.
    """

    model_config = ConfigDict(extra="forbid")

    company_id: UUID
