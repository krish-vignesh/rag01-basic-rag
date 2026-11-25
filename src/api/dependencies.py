from typing import cast

from fastapi import Request

from src.services.ingestion import DocumentIngestionService


def get_ingestion_service(
    request: Request,
) -> DocumentIngestionService:
    return cast(
        DocumentIngestionService,
        request.app.state.ingestion_service,
    )
