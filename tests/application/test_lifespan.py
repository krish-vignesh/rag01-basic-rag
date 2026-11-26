
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI

import src.application.lifespan as lifespan_module


@pytest.fixture
def lifespan_test_environment(monkeypatch):
    """Provide isolated dependencies for application lifespan tests."""

    # --------------------------------------------------
    # 1. Mock shared HTTP client
    # --------------------------------------------------
    http_client = Mock()
    http_client.aclose = AsyncMock()

    http_client_factory = Mock(return_value=http_client)

    monkeypatch.setattr(
        lifespan_module.httpx,
        "AsyncClient",
        http_client_factory,
    )

    # --------------------------------------------------
    # 2. Mock Keycloak JWKS client
    # --------------------------------------------------
    jwks_client = Mock()
    jwks_client_factory = Mock(return_value=jwks_client)

    monkeypatch.setattr(
        lifespan_module,
        "JWKSClient",
        jwks_client_factory,
    )

    # --------------------------------------------------
    # 3. Mock token verifier
    # --------------------------------------------------
    token_verifier = Mock()
    token_verifier_factory = Mock(return_value=token_verifier)

    monkeypatch.setattr(
        lifespan_module,
        "TokenVerifier",
        token_verifier_factory,
    )

    # --------------------------------------------------
    # 4. Mock identity repositories
    # --------------------------------------------------
    user_repository = Mock()
    membership_repository = Mock()
    platform_admin_repository = Mock()

    user_repository_factory = Mock(
        return_value=user_repository
    )

    membership_repository_factory = Mock(
        return_value=membership_repository
    )

    platform_admin_repository_factory = Mock(
        return_value=platform_admin_repository
    )

    monkeypatch.setattr(
        lifespan_module,
        "UserRepository",
        user_repository_factory,
    )

    monkeypatch.setattr(
        lifespan_module,
        "MembershipRepository",
        membership_repository_factory,
    )

    monkeypatch.setattr(
        lifespan_module,
        "PlatformAdminRepository",
        platform_admin_repository_factory,
    )

    # --------------------------------------------------
    # 5. Mock identity resolver
    # --------------------------------------------------
    identity_resolver = Mock()

    identity_resolver_factory = Mock(
        return_value=identity_resolver
    )

    monkeypatch.setattr(
        lifespan_module,
        "IdentityResolver",
        identity_resolver_factory,
    )

    # --------------------------------------------------
    # 6. Mock Azure document storage
    # --------------------------------------------------
    storage = Mock()
    storage.close = AsyncMock()

    storage_factory = Mock(return_value=storage)

    monkeypatch.setattr(
        lifespan_module,
        "DocumentStorage",
        storage_factory,
    )

    # --------------------------------------------------
    # 7. Mock ingestion service
    # --------------------------------------------------
    ingestion_service = Mock()

    ingestion_service_factory = Mock(
        return_value=ingestion_service
    )

    monkeypatch.setattr(
        lifespan_module,
        "DocumentIngestionService",
        ingestion_service_factory,
    )

    # --------------------------------------------------
    # 8. Mock SQLAlchemy engine
    # --------------------------------------------------
    # Do not patch engine.dispose directly.
    # AsyncEngine exposes it as a read-only attribute.

    mock_engine = Mock()
    mock_engine.dispose = AsyncMock()

    monkeypatch.setattr(
        lifespan_module,
        "engine",
        mock_engine,
    )

    # --------------------------------------------------
    # 9. Return test environment
    # --------------------------------------------------
    return SimpleNamespace(
        http_client=http_client,
        http_client_factory=http_client_factory,
        jwks_client=jwks_client,
        jwks_client_factory=jwks_client_factory,
        token_verifier=token_verifier,
        token_verifier_factory=token_verifier_factory,
        user_repository=user_repository,
        user_repository_factory=user_repository_factory,
        membership_repository=membership_repository,
        membership_repository_factory=membership_repository_factory,
        platform_admin_repository=platform_admin_repository,
        platform_admin_repository_factory=platform_admin_repository_factory,
        identity_resolver=identity_resolver,
        identity_resolver_factory=identity_resolver_factory,
        storage=storage,
        storage_factory=storage_factory,
        ingestion_service=ingestion_service,
        ingestion_service_factory=ingestion_service_factory,
        engine=mock_engine,
    )


@pytest.mark.asyncio
async def test_lifespan_initializes_and_cleans_up_resources(
    lifespan_test_environment,
):
    """Verify successful startup, dependency wiring and shutdown."""

    environment = lifespan_test_environment

    app = FastAPI()

    # --------------------------------------------------
    # 1. Start application lifespan
    # --------------------------------------------------
    async with lifespan_module.lifespan(app):

        # ----------------------------------------------
        # Verify application state
        # ----------------------------------------------
        assert (
            app.state.token_verifier
            is environment.token_verifier
        )

        assert (
            app.state.identity_resolver
            is environment.identity_resolver
        )

        assert (
            app.state.ingestion_service
            is environment.ingestion_service
        )

        # ----------------------------------------------
        # Verify HTTP client initialization
        # ----------------------------------------------
        environment.http_client_factory.assert_called_once_with()

        # ----------------------------------------------
        # Verify JWKS client initialization
        # ----------------------------------------------
        environment.jwks_client_factory.assert_called_once_with(
            jwks_url=lifespan_module.settings.keycloak_jwks_url,
            http_client=environment.http_client,
        )

        # ----------------------------------------------
        # Verify token verifier initialization
        # ----------------------------------------------
        environment.token_verifier_factory.assert_called_once_with(
            jwks_client=environment.jwks_client,
            issuer=lifespan_module.settings.keycloak_issuer,
            audience=lifespan_module.settings.keycloak_audience,
        )

        # ----------------------------------------------
        # Verify identity repository initialization
        # ----------------------------------------------
        environment.user_repository_factory.assert_called_once_with()

        environment.membership_repository_factory.assert_called_once_with()

        environment.platform_admin_repository_factory.assert_called_once_with()

        # ----------------------------------------------
        # Verify identity resolver initialization
        # ----------------------------------------------
        environment.identity_resolver_factory.assert_called_once_with(
            user_repository=environment.user_repository,
            membership_repository=environment.membership_repository,
            platform_admin_repository=environment.platform_admin_repository,
        )

        # ----------------------------------------------
        # Verify document storage initialization
        # ----------------------------------------------
        environment.storage_factory.assert_called_once_with(
            storage_account_url=(
                lifespan_module.settings.azure_storage_account_url
            ),
            container_name=(
                lifespan_module.settings.azure_storage_container_name
            ),
        )

        # ----------------------------------------------
        # Verify ingestion service initialization
        # ----------------------------------------------
        environment.ingestion_service_factory.assert_called_once_with(
            session_factory=lifespan_module.AsyncSessionFactory,
            storage=environment.storage,
        )

        # Resources should remain open during lifespan.
        environment.storage.close.assert_not_awaited()
        environment.http_client.aclose.assert_not_awaited()
        environment.engine.dispose.assert_not_awaited()

    # --------------------------------------------------
    # 2. Verify shutdown cleanup
    # --------------------------------------------------
    environment.storage.close.assert_awaited_once()

    environment.http_client.aclose.assert_awaited_once()

    environment.engine.dispose.assert_awaited_once()
