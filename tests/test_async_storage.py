"""Verification of asynchronous Azure storage boundaries."""

import asyncio
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import src.storage.storage as storage_module
from src.storage.storage import DocumentStorage


@pytest.fixture
def azure_clients(monkeypatch):
    credential = SimpleNamespace(close=AsyncMock())
    blob = SimpleNamespace(
        upload_blob=AsyncMock(),
        download_blob=AsyncMock(),
        exists=AsyncMock(return_value=True),
        delete_blob=AsyncMock(),
    )
    container = SimpleNamespace(
        get_blob_client=lambda _blob_name: blob,
    )
    service_client = SimpleNamespace(
        get_container_client=lambda _container_name: container,
        close=AsyncMock(),
    )

    monkeypatch.setattr(
        DocumentStorage,
        "_create_credential",
        staticmethod(lambda: credential),
    )
    monkeypatch.setattr(
        storage_module,
        "BlobServiceClient",
        lambda **_kwargs: service_client,
    )

    return SimpleNamespace(
        credential=credential,
        blob=blob,
        container=container,
        service_client=service_client,
    )


@pytest.fixture
def storage(azure_clients) -> DocumentStorage:
    return DocumentStorage(
        storage_account_url="https://test.blob.core.windows.net",
        container_name="documents",
    )


@pytest.mark.asyncio
async def test_async_upload_exists_download_and_delete(
    storage: DocumentStorage,
    azure_clients,
) -> None:
    download_stream = SimpleNamespace(readinto=AsyncMock())
    download_stream.readinto.side_effect = lambda target: target.write(
        b"downloaded content"
    )
    azure_clients.blob.download_blob.return_value = download_stream

    await storage.save_document(
        stream=BytesIO(b"upload content"),
        company_id="company",
        document_id="document",
        filename="file.txt",
        content_type="text/plain",
    )
    assert azure_clients.blob.upload_blob.await_count == 1
    upload_kwargs = azure_clients.blob.upload_blob.await_args.kwargs
    assert upload_kwargs["overwrite"] is False
    assert upload_kwargs["content_settings"].content_type == "text/plain"

    assert await storage.exists("company", "document", "file.txt") is True
    downloaded = await storage.download_document(
        "company",
        "document",
        "file.txt",
    )
    try:
        assert downloaded.read() == b"downloaded content"
    finally:
        downloaded.close()

    await storage.delete_document("company", "document", "file.txt")
    assert azure_clients.blob.delete_blob.await_count == 1


@pytest.mark.asyncio
async def test_close_attempts_both_resources_and_is_idempotent(
    storage: DocumentStorage,
    azure_clients,
) -> None:
    await storage.close()
    await storage.close()

    azure_clients.service_client.close.assert_awaited_once()
    azure_clients.credential.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_close_retries_resource_that_failed(
    storage: DocumentStorage,
    azure_clients,
) -> None:
    azure_clients.service_client.close.side_effect = [
        RuntimeError("service close failed"),
        None,
    ]

    await storage.close()

    assert azure_clients.service_client.close.await_count == 2
    assert azure_clients.credential.close.await_count == 1


@pytest.mark.asyncio
async def test_close_attempts_credential_after_service_cancellation(
    storage: DocumentStorage,
    azure_clients,
) -> None:
    azure_clients.service_client.close.side_effect = asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await storage.close()

    azure_clients.service_client.close.assert_awaited_once()
    azure_clients.credential.close.assert_awaited_once()
    assert storage._service_client_closed is False
    assert storage._credential_closed is True


@pytest.mark.asyncio
async def test_close_retries_credential_cleanup(
    storage: DocumentStorage,
    azure_clients,
) -> None:
    azure_clients.credential.close.side_effect = [
        RuntimeError("credential close failed"),
        None,
    ]

    await storage.close()

    assert azure_clients.service_client.close.await_count == 1
    assert azure_clients.credential.close.await_count == 2
    assert storage._service_client_closed is True
    assert storage._credential_closed is True


@pytest.mark.asyncio
async def test_close_reports_exhausted_cleanup_and_retries_later(
    storage: DocumentStorage,
    azure_clients,
) -> None:
    azure_clients.service_client.close.side_effect = RuntimeError(
        "service close failed"
    )

    with pytest.raises(ExceptionGroup):
        await storage.close()

    assert azure_clients.service_client.close.await_count == 2
    assert azure_clients.credential.close.await_count == 1
    assert storage._service_client_closed is False
    assert storage._credential_closed is True

    azure_clients.service_client.close.side_effect = None
    await storage.close()

    assert azure_clients.service_client.close.await_count == 3
    assert azure_clients.credential.close.await_count == 1
    assert storage._service_client_closed is True


@pytest.mark.asyncio
async def test_close_propagates_credential_cancellation(
    storage: DocumentStorage,
    azure_clients,
) -> None:
    azure_clients.credential.close.side_effect = asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await storage.close()

    azure_clients.service_client.close.assert_awaited_once()
    azure_clients.credential.close.assert_awaited_once()
    assert storage._service_client_closed is True
    assert storage._credential_closed is False


@pytest.mark.asyncio
async def test_close_preserves_cancellation_with_ordinary_cleanup_failure(
    storage: DocumentStorage,
    azure_clients,
) -> None:
    azure_clients.service_client.close.side_effect = RuntimeError(
        "service close failed"
    )
    azure_clients.credential.close.side_effect = asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await storage.close()

    assert azure_clients.service_client.close.await_count == 2
    assert azure_clients.credential.close.await_count == 1
    assert storage._service_client_closed is False
    assert storage._credential_closed is False


@pytest.mark.asyncio
async def test_close_attempts_both_resources_when_both_are_cancelled(
    storage: DocumentStorage,
    azure_clients,
) -> None:
    azure_clients.service_client.close.side_effect = asyncio.CancelledError()
    azure_clients.credential.close.side_effect = asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await storage.close()

    azure_clients.service_client.close.assert_awaited_once()
    azure_clients.credential.close.assert_awaited_once()
    assert storage._service_client_closed is False
    assert storage._credential_closed is False


@pytest.mark.asyncio
async def test_context_manager_closes_storage(
    storage: DocumentStorage,
    azure_clients,
) -> None:
    async with storage:
        pass

    azure_clients.service_client.close.assert_awaited_once()
    azure_clients.credential.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_upload_error_propagates(storage: DocumentStorage, azure_clients) -> None:
    azure_clients.blob.upload_blob.side_effect = OSError("upload failed")

    with pytest.raises(OSError, match="upload failed"):
        await storage.save_document(
            stream=BytesIO(b"content"),
            company_id="company",
            document_id="document",
            filename="file.txt",
        )
