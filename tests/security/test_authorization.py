
from uuid import uuid4

import pytest

from src.models.enum import CompanyRole
from src.security.authorization import (
    CompanyScopeViolationError,
    DepartmentScopeViolationError,
    InsufficientCompanyRoleError,
    MissingCompanyMembershipError,
    PlatformAdminRequiredError,
    require_company_membership,
    require_company_role,
    require_company_scope,
    require_department_scope,
    require_platform_admin,
)
from src.security.principal import (
    AuthenticatedPrincipal,
    CompanyMembershipContext,
    PlatformAdminContext,
)


@pytest.fixture
def company_membership() -> CompanyMembershipContext:
    return CompanyMembershipContext(
        membership_id=uuid4(),
        company_id=uuid4(),
        department_id=uuid4(),
        role_code=CompanyRole.OPERATOR,
    )


@pytest.fixture
def company_principal(
    company_membership: CompanyMembershipContext,
) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        user_id=uuid4(),
        keycloak_sub="test-user-123",
        company_membership=company_membership,
        platform_admin=None,
    )


@pytest.fixture
def platform_admin_principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        user_id=uuid4(),
        keycloak_sub="platform-admin-123",
        company_membership=None,
        platform_admin=PlatformAdminContext(
            platform_admin_id=101,
        ),
    )


@pytest.fixture
def company_owner_principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        user_id=uuid4(),
        keycloak_sub="company-owner-123",
        company_membership=CompanyMembershipContext(
            membership_id=uuid4(),
            company_id=uuid4(),
            department_id=None,
            role_code=CompanyRole.COMPANY_OWNER,
        ),
        platform_admin=None,
    )


# ---------------------------------------------------------
# Company membership tests
# ---------------------------------------------------------


def test_require_company_membership_returns_membership(
    company_principal: AuthenticatedPrincipal,
    company_membership: CompanyMembershipContext,
) -> None:
    result = require_company_membership(company_principal)

    assert result is company_membership


def test_require_company_membership_rejects_missing_membership(
    platform_admin_principal: AuthenticatedPrincipal,
) -> None:
    with pytest.raises(MissingCompanyMembershipError):
        require_company_membership(platform_admin_principal)


# ---------------------------------------------------------
# Company role tests
# ---------------------------------------------------------


def test_require_company_role_allows_permitted_role(
    company_principal: AuthenticatedPrincipal,
    company_membership: CompanyMembershipContext,
) -> None:
    result = require_company_role(
        company_principal,
        allowed_roles={CompanyRole.OPERATOR, CompanyRole.COMPANY_OWNER},
    )

    assert result is company_membership


def test_require_company_role_rejects_unpermitted_role(
    company_principal: AuthenticatedPrincipal,
) -> None:
    with pytest.raises(InsufficientCompanyRoleError):
        require_company_role(
            company_principal,
            allowed_roles={CompanyRole.COMPANY_OWNER},
        )


def test_require_company_role_rejects_empty_allowed_roles(
    company_principal: AuthenticatedPrincipal,
) -> None:
    with pytest.raises(ValueError, match="At least one allowed company role"):
        require_company_role(
            company_principal,
            allowed_roles=set(),
        )


# ---------------------------------------------------------
# Company scope tests
# ---------------------------------------------------------


def test_require_company_scope_allows_matching_company(
    company_principal: AuthenticatedPrincipal,
    company_membership: CompanyMembershipContext,
) -> None:
    result = require_company_scope(
        company_principal,
        company_id=company_membership.company_id,
    )

    assert result is company_membership


def test_require_company_scope_rejects_different_company(
    company_principal: AuthenticatedPrincipal,
) -> None:
    with pytest.raises(CompanyScopeViolationError):
        require_company_scope(
            company_principal,
            company_id=uuid4(),
        )


# ---------------------------------------------------------
# Department scope tests
# ---------------------------------------------------------



def test_require_department_scope_allows_own_department(
    company_principal: AuthenticatedPrincipal,
    company_membership: CompanyMembershipContext,
) -> None:
    result = require_department_scope(
        company_principal,
        company_id=company_membership.company_id,
        department_id=company_membership.department_id,
    )

    assert result is company_membership


def test_require_department_scope_rejects_other_department(
    company_principal: AuthenticatedPrincipal,
) -> None:
    with pytest.raises(DepartmentScopeViolationError):
        require_department_scope(
            company_principal,
            company_id=company_principal.company_membership.company_id,
            department_id=uuid4(),
        )


def test_require_department_scope_allows_company_owner(
    company_owner_principal: AuthenticatedPrincipal,
) -> None:
    result = require_department_scope(
        company_owner_principal,
        company_id=company_owner_principal.company_membership.company_id,
        department_id=uuid4(),
    )

    assert result is company_owner_principal.company_membership


def test_require_department_scope_rejects_user_without_membership(
    platform_admin_principal: AuthenticatedPrincipal,
) -> None:
    with pytest.raises(MissingCompanyMembershipError):
        require_department_scope(
            platform_admin_principal,
            company_id=uuid4(),
            department_id=uuid4(),
        )


# ---------------------------------------------------------
# Platform admin tests
# ---------------------------------------------------------


def test_require_platform_admin_returns_platform_context(
    platform_admin_principal: AuthenticatedPrincipal,
) -> None:
    result = require_platform_admin(platform_admin_principal)

    assert result is platform_admin_principal.platform_admin
    assert result.platform_admin_id == 101


def test_require_platform_admin_rejects_non_admin(
    company_principal: AuthenticatedPrincipal,
) -> None:
    with pytest.raises(PlatformAdminRequiredError):
        require_platform_admin(company_principal)


def test_require_department_scope_rejects_company_owner_from_another_company(
    company_owner_principal: AuthenticatedPrincipal,
) -> None:
    with pytest.raises(CompanyScopeViolationError):
        require_department_scope(
            company_owner_principal,
            company_id=uuid4(),
            department_id=uuid4(),
        )