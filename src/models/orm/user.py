import uuid

from sqlalchemy import String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base
from src.models.mixin import TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    __table_args__ = (
        UniqueConstraint(
            "keycloak_sub",
            name="uq_users_keycloak_sub",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    keycloak_sub: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )

    display_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
