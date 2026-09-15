import uuid

from pydantic import BaseModel, Field


class Chunk(BaseModel):

    chunk_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )

    document_id: str

    company_id: str

    chunk_text: str

    chunk_index: int

    page: int | None = None

    source: str | None = None