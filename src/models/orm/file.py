from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.orm.document import Document


class File(Base):
    __tablename__ = "files"

    documents: Mapped[list["Document"]] = relationship(back_populates="file")

    file_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
