import uuid

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base
from src.models.mixin import CreatedAtMixin


class MembershipAuditEvent(CreatedAtMixin, Base):
    __tablename__ = "membership_audit_events"

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company_memberships.membership_id"),
        nullable=False,
    )

    actor_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company_memberships.membership_id"),
        nullable=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    old_values: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    new_values: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
