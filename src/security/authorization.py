
from collections.abc import Collection
from uuid import UUID

from src.models.enum import CompanyRole
from src.security.principal import (
    AuthenticatedPrincipal,
    CompanyMembershipContext,
    PlatformAdminContext,
)


class AuthorizationError(Exception):
    """Base exception for application authorization failures."""


class MissingCompanyMembershipError(AuthorizationError):
    """Raised when the principal has no active company membership."""


class InsufficientCompanyRoleError(AuthorizationError):
    """Raised when the company role is not permitted for an operation."""


class CompanyScopeViolationError(AuthorizationError):
    """Raised when the principal accesses another company."""


class DepartmentScopeViolationError(AuthorizationError):
    """Raised when the principal accesses an unauthorized department."""


class PlatformAdminRequiredError(AuthorizationError):
    """Raised when an operation requires platform-admin access."""


def require_company_membership(
    principal: AuthenticatedPrincipal,
) -> CompanyMembershipContext:
    """Return the active company membership or reject the operation."""
    membership = principal.company_membership

    if membership is None:
        raise MissingCompanyMembershipError(
            "Active company membership is required."
        )

    return membership


def require_company_role(
    principal: AuthenticatedPrincipal,
    allowed_roles: Collection[CompanyRole],
) -> CompanyMembershipContext:
    """Require the principal to have one of the specified company roles."""
    roles = frozenset(allowed_roles)

    if not roles:
        raise ValueError("At least one allowed company role must be provided.")

    membership = require_company_membership(principal)

    if membership.role_code not in roles:
        raise InsufficientCompanyRoleError(
            "Your company role does not permit this operation."
        )

    return membership


def require_company_scope(
    principal: AuthenticatedPrincipal,
    company_id: UUID,
) -> CompanyMembershipContext:
    """Require the requested company to match the membership's company."""
    membership = require_company_membership(principal)

    if membership.company_id != company_id:
        raise CompanyScopeViolationError(
            "You do not have access to this company."
        )

    return membership


def require_department_scope(
    principal: AuthenticatedPrincipal,
    company_id: UUID,
    department_id: UUID,
) -> CompanyMembershipContext:
    """Require access to a department within the principal's company."""
    membership = require_company_scope(principal, company_id)

    if (
        membership.role_code != CompanyRole.COMPANY_OWNER
        and membership.department_id != department_id
    ):
        raise DepartmentScopeViolationError(
            "You do not have access to this department."
        )

    return membership


def require_platform_admin(
    principal: AuthenticatedPrincipal,
) -> PlatformAdminContext:
    """Require an active platform-admin context."""
    platform_admin = principal.platform_admin

    if platform_admin is None:
        raise PlatformAdminRequiredError(
            "Platform administrator access is required."
        )

    return platform_admin
