from enum import StrEnum


class CompanyRole(StrEnum):
    """Fixed organizational roles within a company."""

    COMPANY_OWNER = "COMPANY_OWNER"
    DEPARTMENT_MANAGER = "DEPARTMENT_MANAGER"
    OPERATOR = "OPERATOR"
    EMPLOYEE = "EMPLOYEE"


class DepartmentType(StrEnum):
    """Controlled classifications for company departments."""

    HR = "HR"
    IT_SUPPORT = "IT_SUPPORT"
    GENERAL = "GENERAL"


class InvitationStatus(StrEnum):
    """Lifecycle states of an invitation."""

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
