"""Verification of asynchronous FastAPI route integration."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from src.api.dependencies import get_ingestion_service
from src.api.routes.batch_documents import router as batch_router
from src.api.routes.documents import router as documents_router
from src.services.ingestion import (
    DocumentIngestionResult,
    DocumentUploadError,
    DuplicateDocumentError,
)


def _document_result(filename: str) -> DocumentIngestionResult:
    return DocumentIngestionResult(
        document=SimpleNamespace(
            document_id=uuid4(),
            company_id=uuid4(),
            filename=filename,
            status="uploaded",
        ),
        recovered=False,
    )


@pytest.fixture
def api_app():
    app = FastAPI()
    app.include_router(documents_router)
    app.include_router(batch_router)
    return app


async def _request(app, method: str, url: str, **kwargs) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        return await client.request(method, url, **kwargs)


@pytest.mark.asyncio
async def test_single_upload_uses_injected_async_service(api_app) -> None:
    service = SimpleNamespace(ingest_document=AsyncMock())
    service.ingest_document.return_value = _document_result("file.txt")
    api_app.dependency_overrides[get_ingestion_service] = lambda: service

    response = await _request(
        api_app,
        "POST",
        "/documents",
        data={"company_id": str(uuid4())},
        files={"file": ("file.txt", b"content", "text/plain")},
    )

    assert response.status_code == 201
    service.ingest_document.assert_awaited_once()


@pytest.mark.asyncio
async def test_single_upload_maps_duplicate_error(api_app) -> None:
    service = SimpleNamespace(ingest_document=AsyncMock())
    service.ingest_document.side_effect = DuplicateDocumentError("duplicate")
    api_app.dependency_overrides[get_ingestion_service] = lambda: service

    response = await _request(
        api_app,
        "POST",
        "/documents",
        data={"company_id": str(uuid4())},
        files={"file": ("file.txt", b"content", "text/plain")},
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_batch_upload_is_sequential_and_preserves_partial_success(
    api_app,
) -> None:
    service = SimpleNamespace(ingest_document=AsyncMock())
    service.ingest_document.side_effect = [
        _document_result("one.txt"),
        DuplicateDocumentError("duplicate"),
        _document_result("three.txt"),
    ]
    api_app.dependency_overrides[get_ingestion_service] = lambda: service

    response = await _request(
        api_app,
        "POST",
        "/documents/batch",
        data={"company_id": str(uuid4())},
        files=[
            ("files", ("one.txt", b"one", "text/plain")),
            ("files", ("two.txt", b"two", "text/plain")),
            ("files", ("three.txt", b"three", "text/plain")),
        ],
    )

    body = response.json()
    assert response.status_code == 200
    assert body["successful_uploads"] == 2
    assert body["failed_uploads"] == 1
    assert body["not_processed"] == 0
    assert service.ingest_document.await_count == 3


@pytest.mark.asyncio
async def test_upload_error_maps_to_bad_gateway(api_app) -> None:
    service = SimpleNamespace(ingest_document=AsyncMock())
    service.ingest_document.side_effect = DocumentUploadError("failed")
    api_app.dependency_overrides[get_ingestion_service] = lambda: service

    response = await _request(
        api_app,
        "POST",
        "/documents",
        data={"company_id": str(uuid4())},
        files={"file": ("file.txt", b"content", "text/plain")},
    )

    assert response.status_code == 502
