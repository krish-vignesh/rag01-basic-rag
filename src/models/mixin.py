from datetime import datetime

from sqlalchemy import DateTime, text
from sqlalchemy.orm import Mapped, mapped_column


class CreatedAtMixin:
    """Provides a database-managed creation timestamp."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class TimestampMixin(CreatedAtMixin):
    """Provides creation and update timestamps."""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
    )
