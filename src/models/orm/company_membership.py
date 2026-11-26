import uuid

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    String,
    UniqueConstraint,
    text,
    ForeignKeyConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base
from src.models.enum import CompanyRole
from src.models.mixin import TimestampMixin


class CompanyMembership(TimestampMixin, Base):
    __tablename__ = "company_memberships"

    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "department_id"],
            ["departments.company_id", "departments.department_id"],
            name="fk_memberships_company_department",
        ),
        UniqueConstraint(
            "company_id",
            "membership_id",
            name="uq_company_memberships_company_membership",
        ),
        UniqueConstraint(
            "user_id",
            name="uq_company_memberships_user_id",
        ),
        CheckConstraint(
            "role_code IN ("
            "'COMPANY_OWNER', "
            "'DEPARTMENT_MANAGER', "
            "'OPERATOR', "
            "'EMPLOYEE'"
            ")",
            name="chk_company_memberships_role_code",
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
            name="chk_company_memberships_role_department",
        ),
    )

    membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.company_id"),
        nullable=False,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id"),
        nullable=False,
    )

    department_id: Mapped[uuid.UUID | None] = mapped_column(
    UUID(as_uuid=True),
    nullable=True,
    )

    role_code: Mapped[CompanyRole] = mapped_column(
        String(50),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'ACTIVE'"),
    )
