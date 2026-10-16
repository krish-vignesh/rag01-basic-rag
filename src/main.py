
import logging

from fastapi import FastAPI

from src.config.logging_config import configure_logging
from src.api.routes.health import router as health_router
from src.api.routes.documents import router as documents_router


configure_logging()

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Hybrid RAG API",
    version="1.0.0",
)

app.include_router(health_router)
app.include_router(documents_router)

logger.info("Hybrid RAG API application initialized")
