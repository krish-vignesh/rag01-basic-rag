import uuid

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base
from src.models.enum import DepartmentType
from src.models.mixin import TimestampMixin


class Department(TimestampMixin, Base):
    __tablename__ = "departments"

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "department_name",
            name="uq_departments_company_name",
        ),
        UniqueConstraint(
            "company_id",
            "department_id",
            name="uq_departments_company_department",
        ),
        CheckConstraint(
            "department_type IN ('HR', 'IT_SUPPORT', 'GENERAL')",
            name="chk_departments_department_type",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="chk_departments_status",
        ),
    )

    department_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.company_id"),
        nullable=False,
    )

    department_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    department_type: Mapped[DepartmentType] = mapped_column(
        String(50),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'ACTIVE'"),
    )
