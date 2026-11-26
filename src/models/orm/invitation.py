import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    text,
    ForeignKeyConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base
from src.models.enum import CompanyRole, InvitationStatus
from src.models.mixin import CreatedAtMixin


class Invitation(CreatedAtMixin, Base):
    __tablename__ = "invitations"

    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "department_id"],
            ["departments.company_id", "departments.department_id"],
            name="fk_invitations_company_department",
        ),
        ForeignKeyConstraint(
            ["company_id", "invited_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.membership_id"],
            name="fk_invitations_company_inviter",
        ),
        UniqueConstraint(
            "token_hash",
            name="uq_invitations_token_hash",
        ),
        CheckConstraint(
            "role_code IN ("
            "'COMPANY_OWNER', "
            "'DEPARTMENT_MANAGER', "
            "'OPERATOR', "
            "'EMPLOYEE'"
            ")",
            name="chk_invitations_role_code",
        ),
        CheckConstraint(
            "("
            "role_code = 'COMPANY_OWNER' "
            "AND department_id IS NULL"
            ") OR ("
            "role_code IN ("
            "'DEPARTMENT_MANAGER', "
            "'OPERATOR', "
            "'EMPLOYEE'"
            ") "
            "AND department_id IS NOT NULL"
            ")",
            name="chk_invitations_role_department",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'ACCEPTED', 'EXPIRED', 'REVOKED')",
            name="chk_invitations_status",
        ),
    )

    invitation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.company_id"),
        nullable=False,
    )

    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    invited_by_membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    invited_email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )

    role_code: Mapped[CompanyRole] = mapped_column(
        String(50),
        nullable=False,
    )

    token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[InvitationStatus] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'PENDING'"),
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    accepted_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id"),
        nullable=True,
    )

    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
