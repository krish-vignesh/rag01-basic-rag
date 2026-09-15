import uuid

from pydantic import BaseModel, Field

from datetime import datetime, timezone


class Document(BaseModel):

    document_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )

    company_id: str

    filename: str

    file_type: str

    version: int

    source: str

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )