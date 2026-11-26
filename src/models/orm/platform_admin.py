import uuid

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base
from src.models.mixin import TimestampMixin


class PlatformAdmin(TimestampMixin, Base):
    __tablename__ = "platform_admins"

    __table_args__ = (
        CheckConstraint(
            "platform_admin_id = 1",
            name="chk_platform_admins_singleton",
        ),
        UniqueConstraint(
            "user_id",
            name="uq_platform_admins_user_id",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'DISABLED')",
            name="chk_platform_admins_status",
        ),
    )

    platform_admin_id: Mapped[int] = mapped_column(
        SmallInteger,
        primary_key=True,
        server_default=text("1"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'ACTIVE'"),
    )
