
import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from src.auth.jwks_client import JWKSClient
from src.auth.token_verifier import TokenVerifier
from src.config.settings import settings
from src.database import AsyncSessionFactory, engine
from src.repositories.membership_repository import MembershipRepository
from src.repositories.platform_admin_repository import (
    PlatformAdminRepository,
)
from src.repositories.user_repository import UserRepository
from src.security.identity_resolver import IdentityResolver
from src.services.ingestion import DocumentIngestionService
from src.storage.storage import DocumentStorage

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(
    app: FastAPI,
) -> AsyncGenerator[None, None]:
    storage: DocumentStorage | None = None
    http_client: httpx.AsyncClient | None = None
    primary_exception: BaseException | None = None

    try:
        # 1. Initialize the shared HTTP client.
        http_client = httpx.AsyncClient()

        # 2. Initialize the Keycloak JWKS client.
        jwks_client = JWKSClient(
            jwks_url=settings.keycloak_jwks_url,
            http_client=http_client,
        )

        # 3. Initialize JWT verification.
        token_verifier = TokenVerifier(
            jwks_client=jwks_client,
            issuer=settings.keycloak_issuer,
            audience=settings.keycloak_audience,
        )

        # 4. Initialize identity repositories.
        user_repository = UserRepository()
        membership_repository = MembershipRepository()
        platform_admin_repository = PlatformAdminRepository()

        # 5. Initialize identity resolution.
        identity_resolver = IdentityResolver(
            user_repository=user_repository,
            membership_repository=membership_repository,
            platform_admin_repository=platform_admin_repository,
        )

        # 6. Initialize existing document storage.
        storage = DocumentStorage(
            storage_account_url=settings.azure_storage_account_url,
            container_name=settings.azure_storage_container_name,
        )

        # 7. Preserve existing ingestion service initialization.
        app.state.ingestion_service = DocumentIngestionService(
            session_factory=AsyncSessionFactory,
            storage=storage,
        )

        # 8. Expose authentication components to request dependencies.
        app.state.token_verifier = token_verifier
        app.state.identity_resolver = identity_resolver

        logger.info("Application resources initialized successfully.")

        yield

    except BaseException as exc:
        primary_exception = exc
        raise

    finally:
        cleanup_errors: list[Exception] = []
        cleanup_cancellations: list[asyncio.CancelledError] = []

        # Close Azure document storage.
        if storage is not None:
            try:
                await storage.close()
            except asyncio.CancelledError as exc:
                cleanup_cancellations.append(exc)
            except Exception as exc:  # noqa: BLE001
                cleanup_errors.append(exc)

        # Close the shared HTTP client.
        if http_client is not None:
            try:
                await http_client.aclose()
            except asyncio.CancelledError as exc:
                cleanup_cancellations.append(exc)
            except Exception as exc:  # noqa: BLE001
                cleanup_errors.append(exc)

        # Dispose of the SQLAlchemy engine.
        try:
            await engine.dispose()
        except asyncio.CancelledError as exc:
            cleanup_cancellations.append(exc)
        except Exception as exc:  # noqa: BLE001
            cleanup_errors.append(exc)

        # Preserve the original startup/runtime exception.
        if primary_exception is not None:
            for cleanup_error in [
                *cleanup_errors,
                *cleanup_cancellations,
            ]:
                logger.error(
                    "Application resource cleanup failed while "
                    "preserving the primary exception.",
                    exc_info=(
                        type(cleanup_error),
                        cleanup_error,
                        cleanup_error.__traceback__,
                    ),
                )

        elif cleanup_cancellations:
            for cleanup_error in cleanup_errors:
                logger.error(
                    "Application resource cleanup failed while "
                    "preserving shutdown cancellation.",
                    exc_info=(
                        type(cleanup_error),
                        cleanup_error,
                        cleanup_error.__traceback__,
                    ),
                )

            raise cleanup_cancellations[0]

        elif cleanup_errors:
            raise ExceptionGroup(
                "Application resource cleanup failed.",
                cleanup_errors,
            )
