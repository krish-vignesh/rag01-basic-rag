
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.enum import CompanyRole
from src.repositories.membership_repository import MembershipRepository
from src.repositories.platform_admin_repository import PlatformAdminRepository
from src.repositories.user_repository import UserRepository
from src.security.principal import (
    AuthenticatedPrincipal,
    CompanyMembershipContext,
    PlatformAdminContext,
)


class IdentityResolutionError(Exception):
    """Base exception for internal identity-resolution failures."""


class InternalUserNotFoundError(IdentityResolutionError):
    """Raised when the verified Keycloak identity has no internal user."""


class NoActiveAccessError(IdentityResolutionError):
    """Raised when the internal user has no active application access."""


class IdentityResolver:
    """Resolve a verified Keycloak identity into an application Principal."""

    def __init__(
        self,
        user_repository: UserRepository,
        membership_repository: MembershipRepository,
        platform_admin_repository: PlatformAdminRepository,
    ) -> None:
        self._user_repository = user_repository
        self._membership_repository = membership_repository
        self._platform_admin_repository = platform_admin_repository

    async def resolve_principal(
        self,
        keycloak_sub: str,
        session: AsyncSession,
    ) -> AuthenticatedPrincipal:
        """
        Resolve the verified Keycloak subject into an internal Principal.

        The supplied request-scoped session is reused for every database query.
        This method does not create, commit, or close the session.
        """

        # 1. Find the internal user linked to this verified Keycloak subject.
        user = await self._user_repository.get_by_keycloak_sub(
            session,
            keycloak_sub,
        )

        if user is None:
            raise InternalUserNotFoundError(
                "No internal user is linked to this identity."
            )

        # 2. Retrieve the user's active company membership, if one exists.
        membership = await self._membership_repository.get_active_by_user_id(
            session,
            user.user_id,
        )

        # 3. Retrieve the user's active platform-admin record, if one exists.
        platform_admin = (
            await self._platform_admin_repository.get_active_by_user_id(
                session,
                user.user_id,
            )
        )

        # 4. The user must have at least one active application access record.
        if membership is None and platform_admin is None:
            raise NoActiveAccessError(
                "The user has no active application access."
            )

        # 5. Convert the database records into independent context objects.
        company_context = None

        if membership is not None:
            company_context = CompanyMembershipContext(
                membership_id=membership.membership_id,
                company_id=membership.company_id,
                department_id=membership.department_id,
                role_code=CompanyRole(membership.role_code),
            )

        platform_admin_context = None

        if platform_admin is not None:
            platform_admin_context = PlatformAdminContext(
                platform_admin_id=platform_admin.platform_admin_id,
            )

        # 6. Return the trusted application identity context.
        return AuthenticatedPrincipal(
            user_id=user.user_id,
            keycloak_sub=user.keycloak_sub,
            company_membership=company_context,
            platform_admin=platform_admin_context,
        )
