
from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Annotated
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session
from src.auth.token_verifier import (
    InvalidAccessTokenError,
    TokenVerificationUnavailableError,
)
from src.models.enum import CompanyRole
from src.security.dependencies import get_current_principal
from src.security.identity_resolver import (
    InternalUserNotFoundError,
    NoActiveAccessError,
)
from src.security.principal import (
    AuthenticatedPrincipal,
    CompanyMembershipContext,
    PlatformAdminContext,
)


def build_company_principal() -> AuthenticatedPrincipal:
    """Build a principal with active company membership."""
    return AuthenticatedPrincipal(
        user_id=uuid4(),
        keycloak_sub="keycloak-user-123",
        company_membership=CompanyMembershipContext(
            membership_id=uuid4(),
            company_id=uuid4(),
            department_id=uuid4(),
            role_code=CompanyRole.OPERATOR,
        ),
        platform_admin=None,
    )


def build_platform_admin_principal() -> AuthenticatedPrincipal:
    """Build a principal with active platform-admin access."""
    return AuthenticatedPrincipal(
        user_id=uuid4(),
        keycloak_sub="keycloak-user-123",
        company_membership=None,
        platform_admin=PlatformAdminContext(
            platform_admin_id=101,
        ),
    )


def build_combined_principal() -> AuthenticatedPrincipal:
    """Build a principal with both application access contexts."""
    return AuthenticatedPrincipal(
        user_id=uuid4(),
        keycloak_sub="keycloak-user-123",
        company_membership=CompanyMembershipContext(
            membership_id=uuid4(),
            company_id=uuid4(),
            department_id=uuid4(),
            role_code=CompanyRole.COMPANY_OWNER,
        ),
        platform_admin=PlatformAdminContext(
            platform_admin_id=202,
        ),
    )


@pytest.fixture
async def security_flow_client() -> AsyncIterator[SimpleNamespace]:
    """Provide an isolated FastAPI application for security-flow tests."""
    app = FastAPI()

    session = AsyncMock(spec=AsyncSession)

    token_verifier = SimpleNamespace(
        verify_access_token=AsyncMock(
            return_value={"sub": "keycloak-user-123"}
        )
    )

    identity_resolver = SimpleNamespace(
        resolve_principal=AsyncMock()
    )

    app.state.token_verifier = token_verifier
    app.state.identity_resolver = identity_resolver

    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    @app.get("/protected")
    async def protected_endpoint(
        principal: Annotated[
            AuthenticatedPrincipal,
            Depends(get_current_principal),
        ],
    ) -> dict:
        membership = principal.company_membership
        platform_admin = principal.platform_admin

        return {
            "user_id": str(principal.user_id),
            "keycloak_sub": principal.keycloak_sub,
            "company_membership": (
                {
                    "membership_id": str(membership.membership_id),
                    "company_id": str(membership.company_id),
                    "department_id": (
                        str(membership.department_id)
                        if membership.department_id is not None
                        else None
                    ),
                    "role_code": membership.role_code.value,
                }
                if membership is not None
                else None
            ),
            "platform_admin": (
                {
                    "platform_admin_id": platform_admin.platform_admin_id,
                }
                if platform_admin is not None
                else None
            ),
        }

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield SimpleNamespace(
            app=app,
            client=client,
            session=session,
            token_verifier=token_verifier,
            identity_resolver=identity_resolver,
        )


@pytest.mark.asyncio
async def test_missing_bearer_token_returns_401(
    security_flow_client: SimpleNamespace,
) -> None:
    response = await security_flow_client.client.get("/protected")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"

    security_flow_client.token_verifier.verify_access_token.assert_not_awaited()
    security_flow_client.identity_resolver.resolve_principal.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalid_access_token_returns_401(
    security_flow_client: SimpleNamespace,
) -> None:
    security_flow_client.token_verifier.verify_access_token.side_effect = (
        InvalidAccessTokenError("Invalid token.")
    )

    response = await security_flow_client.client.get(
        "/protected",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    security_flow_client.token_verifier.verify_access_token.assert_awaited_once_with(
        "invalid-token"
    )
    security_flow_client.identity_resolver.resolve_principal.assert_not_awaited()


@pytest.mark.asyncio
async def test_token_verification_unavailable_returns_503(
    security_flow_client: SimpleNamespace,
) -> None:
    security_flow_client.token_verifier.verify_access_token.side_effect = (
        TokenVerificationUnavailableError("JWKS unavailable.")
    )

    response = await security_flow_client.client.get(
        "/protected",
        headers={"Authorization": "Bearer valid-looking-token"},
    )

    assert response.status_code == 503
    security_flow_client.identity_resolver.resolve_principal.assert_not_awaited()


@pytest.mark.asyncio
async def test_unknown_internal_user_returns_401(
    security_flow_client: SimpleNamespace,
) -> None:
    security_flow_client.identity_resolver.resolve_principal.side_effect = (
        InternalUserNotFoundError("Internal user not found.")
    )

    response = await security_flow_client.client.get(
        "/protected",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 401
    security_flow_client.identity_resolver.resolve_principal.assert_awaited_once_with(
        keycloak_sub="keycloak-user-123",
        session=security_flow_client.session,
    )


@pytest.mark.asyncio
async def test_user_without_active_access_returns_403(
    security_flow_client: SimpleNamespace,
) -> None:
    security_flow_client.identity_resolver.resolve_principal.side_effect = (
        NoActiveAccessError("No active access.")
    )

    response = await security_flow_client.client.get(
        "/protected",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_active_company_membership_reaches_protected_endpoint(
    security_flow_client: SimpleNamespace,
) -> None:
    principal = build_company_principal()

    security_flow_client.identity_resolver.resolve_principal.return_value = (
        principal
    )

    response = await security_flow_client.client.get(
        "/protected",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["user_id"] == str(principal.user_id)
    assert body["keycloak_sub"] == principal.keycloak_sub
    assert body["company_membership"]["membership_id"] == str(
        principal.company_membership.membership_id
    )
    assert body["company_membership"]["company_id"] == str(
        principal.company_membership.company_id
    )
    assert body["company_membership"]["role_code"] == "OPERATOR"
    assert body["platform_admin"] is None

    security_flow_client.identity_resolver.resolve_principal.assert_awaited_once_with(
        keycloak_sub="keycloak-user-123",
        session=security_flow_client.session,
    )


@pytest.mark.asyncio
async def test_active_platform_admin_reaches_protected_endpoint(
    security_flow_client: SimpleNamespace,
) -> None:
    principal = build_platform_admin_principal()

    security_flow_client.identity_resolver.resolve_principal.return_value = (
        principal
    )

    response = await security_flow_client.client.get(
        "/protected",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["company_membership"] is None
    assert body["platform_admin"]["platform_admin_id"] == 101


@pytest.mark.asyncio
async def test_both_access_contexts_are_preserved(
    security_flow_client: SimpleNamespace,
) -> None:
    principal = build_combined_principal()

    security_flow_client.identity_resolver.resolve_principal.return_value = (
        principal
    )

    response = await security_flow_client.client.get(
        "/protected",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["company_membership"] is not None
    assert body["company_membership"]["role_code"] == "COMPANY_OWNER"
    assert body["platform_admin"]["platform_admin_id"] == 202
