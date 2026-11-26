
from dataclasses import dataclass
from uuid import UUID

from src.models.enum import CompanyRole


@dataclass(frozen=True, slots=True)
class CompanyMembershipContext:
    """Represents the authenticated user's active company membership."""

    membership_id: UUID
    company_id: UUID
    department_id: UUID | None
    role_code: CompanyRole


@dataclass(frozen=True, slots=True)
class PlatformAdminContext:
    """Represents the authenticated user's active platform-admin access."""

    platform_admin_id: int


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    """Trusted identity and access context for the current API request."""

    user_id: UUID
    keycloak_sub: str
    company_membership: CompanyMembershipContext | None
    platform_admin: PlatformAdminContext | None
