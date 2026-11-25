"""Verification of asynchronous ingestion orchestration."""

import asyncio
import threading
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

import pytest

import src.services.ingestion as ingestion_module
from src.services.ingestion import (
    DocumentIngestionResult,
    DocumentIngestionService,
    DocumentUploadError,
)


def _configure_new_document(bundle, document):
    bundle.document_repository.create.return_value = SimpleNamespace(
        document_id=document.document_id,
        company_id=document.company_id,
        file_id="",
        filename=document.filename,
        status="pending",
    )
    bundle.document_repository.update_status.return_value = SimpleNamespace(
        document_id=document.document_id,
        company_id=document.company_id,
        filename=document.filename,
        status="uploaded",
    )


@pytest.mark.asyncio
async def test_ingestion_preserves_transaction_order_and_awaits_storage(
    ingestion_bundle,
    document,
    file_stream,
) -> None:
    _configure_new_document(ingestion_bundle, document)
    file_stream.seek(3)

    result = await ingestion_bundle.service.ingest_document(
        document,
        file_stream,
        content_type="text/plain",
        return_result=True,
    )

    assert isinstance(result, DocumentIngestionResult)
    assert result.document.status == "uploaded"
    assert ingestion_bundle.storage.upload_positions == [0]
    assert ingestion_bundle.session_factory.committed == 2
    assert ingestion_bundle.storage.calls == [("save", "fixture.txt")]
    ingestion_bundle.company_repository.get_by_id.assert_awaited_once()
    assert (
        ingestion_bundle.document_repository.get_by_company_and_file.call_args.kwargs[
            "for_update"
        ]
        is True
    )
    ingestion_bundle.document_repository.update_status.assert_awaited_once()


@pytest.mark.asyncio
async def test_failed_document_recovery_verifies_existing_blob(
    ingestion_bundle,
    document,
) -> None:
    content = b"recoverable document"
    blob_name = ingestion_bundle.storage.build_blob_name(
        str(document.company_id),
        str(document.document_id),
        document.filename,
    )
    existing_document = SimpleNamespace(
        status="failed",
        company_id=document.company_id,
        document_id=document.document_id,
        filename=document.filename,
        blob_name=blob_name,
    )
    updated_document = SimpleNamespace(
        document_id=document.document_id,
        company_id=document.company_id,
        filename=document.filename,
        status="uploaded",
    )
    ingestion_bundle.document_repository.get_by_company_and_file.return_value = (
        existing_document
    )
    ingestion_bundle.document_repository.update_status.return_value = updated_document
    ingestion_bundle.storage.blobs[blob_name] = content

    result = await ingestion_bundle.service.ingest_document(
        document,
        BytesIO(content),
        return_result=True,
    )

    assert result.recovered is True
    assert result.document is updated_document
    assert ("exists", document.filename) in ingestion_bundle.storage.calls
    assert ("download", document.filename) in ingestion_bundle.storage.calls
    assert not any(
        operation == "save" for operation, _filename in ingestion_bundle.storage.calls
    )
    assert ingestion_bundle.session_factory.committed == 1


@pytest.mark.asyncio
async def test_upload_failure_records_failed_status(
    ingestion_bundle,
    document,
    file_stream,
) -> None:
    _configure_new_document(ingestion_bundle, document)
    ingestion_bundle.storage.upload_error = OSError("storage unavailable")
    ingestion_bundle.document_repository.update_status.return_value = SimpleNamespace(
        document_id=document.document_id,
        status="failed",
    )

    with pytest.raises(DocumentUploadError, match="status is 'failed'"):
        await ingestion_bundle.service.ingest_document(
            document,
            file_stream,
            return_result=True,
        )

    assert ingestion_bundle.session_factory.committed == 2
    assert (
        ingestion_bundle.document_repository.update_status.call_args.kwargs["status"]
        == "failed"
    )


@pytest.mark.asyncio
async def test_hash_cancellation_waits_for_worker_and_preserves_cancellation(
    ingestion_bundle,
    monkeypatch,
) -> None:
    started = threading.Event()
    release = threading.Event()
    worker_finished_with_open_stream = threading.Event()
    stream = BytesIO(b"hash me")

    def blocking_hash(worker_stream) -> str:
        started.set()
        release.wait(timeout=2)
        if not worker_stream.closed:
            worker_finished_with_open_stream.set()
        return "hash"

    monkeypatch.setattr(
        ingestion_module,
        "calculate_stream_hash",
        blocking_hash,
    )

    task = asyncio.create_task(ingestion_bundle.service._hash_stream_safely(stream))
    await asyncio.to_thread(started.wait, 1)
    task.cancel()
    release.set()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert worker_finished_with_open_stream.is_set()
    stream.close()


@pytest.mark.asyncio
async def test_independent_ingestions_can_overlap_during_storage_wait(
    ingestion_bundle,
    document,
) -> None:
    ingestion_bundle.storage.operation_barrier = asyncio.Event()
    first_document = document
    second_document = document.model_copy(
        update={
            "document_id": uuid4(),
            "filename": "second.txt",
        }
    )

    first_bundle = ingestion_bundle
    second_bundle = SimpleNamespace(
        service=DocumentIngestionService(
            session_factory=ingestion_bundle.session_factory,
            company_repository=SimpleNamespace(
                get_by_id=ingestion_bundle.company_repository.get_by_id
            ),
            file_repository=SimpleNamespace(
                get_by_id=ingestion_bundle.file_repository.get_by_id,
                create=ingestion_bundle.file_repository.create,
            ),
            document_repository=SimpleNamespace(
                get_by_company_and_file=ingestion_bundle.document_repository.get_by_company_and_file,
                create=ingestion_bundle.document_repository.create,
                update_status=ingestion_bundle.document_repository.update_status,
            ),
            storage=ingestion_bundle.storage,
        )
    )
    _configure_new_document(first_bundle, first_document)
    _configure_new_document(
        SimpleNamespace(
            document_repository=second_bundle.service.document_repository,
        ),
        second_document,
    )

    await asyncio.gather(
        first_bundle.service.ingest_document(
            first_document,
            BytesIO(b"first"),
        ),
        second_bundle.service.ingest_document(
            second_document,
            BytesIO(b"second"),
        ),
    )

    assert ingestion_bundle.storage.max_active_operations >= 2
