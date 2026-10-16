
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Document(BaseModel):
    """
    Application-level representation of a document.

    Pydantic validates the document data, while SQLAlchemy ORM models
    define how that data is persisted in PostgreSQL.
    """

    document_id: UUID = Field(default_factory=uuid4)
    company_id: UUID
    filename: str
    file_type: str
    version: int = Field(default=1, ge=1)
    source: str
