import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.orm.company import Company
    from src.models.orm.file import File


class Document(Base):
    __tablename__ = "documents"

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "file_id",
            name="uq_documents_company_file",
        ),
        CheckConstraint(
            "version >= 1",
            name="chk_documents_version",
        ),
        CheckConstraint(
            "status IN ('pending', 'uploaded', 'processing', 'ready', 'failed')",
            name="documents_status_check",
        ),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    company: Mapped["Company"] = relationship(back_populates="documents")

    file: Mapped["File"] = relationship(back_populates="documents")

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.company_id"),
        nullable=False,
    )

    file_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("files.file_id"),
        nullable=False,
    )

    filename: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    file_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("1"),
    )

    source: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    blob_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=text("'pending'"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
