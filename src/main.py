import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routes.batch_documents import router as batch_documents_router
from src.api.routes.documents import router as documents_router
from src.api.routes.health import router as health_router
from src.config.logging_config import configure_logging
from src.config.settings import settings
from src.database import AsyncSessionFactory, engine
from src.services.ingestion import DocumentIngestionService
from src.storage.storage import DocumentStorage

configure_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(
    app: FastAPI,
) -> AsyncGenerator[None, None]:
    storage: DocumentStorage | None = None
    primary_exception: BaseException | None = None

    try:
        storage = DocumentStorage(
            storage_account_url=settings.azure_storage_account_url,
            container_name=settings.azure_storage_container_name,
        )
        app.state.ingestion_service = DocumentIngestionService(
            session_factory=AsyncSessionFactory,
            storage=storage,
        )
        yield
    except BaseException as exc:
        primary_exception = exc
        raise
    finally:
        cleanup_errors: list[Exception] = []
        cleanup_cancellations: list[asyncio.CancelledError] = []

        if storage is not None:
            try:
                await storage.close()
            except asyncio.CancelledError as exc:
                cleanup_cancellations.append(exc)
            except Exception as exc:  # noqa: BLE001
                cleanup_errors.append(exc)

        try:
            await engine.dispose()
        except asyncio.CancelledError as exc:
            cleanup_cancellations.append(exc)
        except Exception as exc:  # noqa: BLE001
            cleanup_errors.append(exc)

        if primary_exception is not None:
            for cleanup_error in [*cleanup_errors, *cleanup_cancellations]:
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


app = FastAPI(
    title="Hybrid RAG API",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(documents_router)
app.include_router(batch_documents_router)

logger.info("Hybrid RAG API application initialized")
