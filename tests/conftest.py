"""Shared pytest fixtures for asynchronous migration verification."""

import asyncio
import sys
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.models.document import Document
from src.services.ingestion import DocumentIngestionService


class FakeAsyncStorage:
    """Controllable asynchronous storage double."""

    def __init__(self) -> None:
        self.blobs: dict[str, bytes] = {}
        self.calls: list[tuple[str, str]] = []
        self.upload_positions: list[int] = []
        self.delay = 0.0
        self.operation_barrier: asyncio.Event | None = None
        self.barrier_waiters = 0
        self.active_operations = 0
        self.max_active_operations = 0
        self.upload_error: Exception | None = None
        self.close_error: Exception | None = None
        self.closed = False

    def build_blob_name(
        self,
        company_id: str,
        document_id: str,
        filename: str,
    ) -> str:
        return f"{company_id}/{document_id}/{filename}"

    async def _wait(self) -> None:
        self.active_operations += 1
        self.max_active_operations = max(
            self.max_active_operations,
            self.active_operations,
        )
        try:
            if self.operation_barrier is not None:
                self.barrier_waiters += 1
                if self.barrier_waiters >= 2:
                    self.operation_barrier.set()
                await self.operation_barrier.wait()
            if self.delay:
                await asyncio.sleep(self.delay)
        finally:
            self.active_operations -= 1

    async def save_document(
        self,
        stream,
        company_id: str,
        document_id: str,
        filename: str,
        content_type: str | None = None,
    ) -> None:
        del content_type
        self.calls.append(("save", filename))
        await self._wait()
        if self.upload_error is not None:
            raise self.upload_error
        self.upload_positions.append(stream.tell())
        self.blobs[self.build_blob_name(company_id, document_id, filename)] = (
            stream.read()
        )

    async def download_document(
        self,
        company_id: str,
        document_id: str,
        filename: str,
    ) -> BytesIO:
        self.calls.append(("download", filename))
        await self._wait()
        blob_name = self.build_blob_name(company_id, document_id, filename)
        if blob_name not in self.blobs:
            raise FileNotFoundError(blob_name)
        return BytesIO(self.blobs[blob_name])

    async def exists(
        self,
        company_id: str,
        document_id: str,
        filename: str,
    ) -> bool:
        self.calls.append(("exists", filename))
        await self._wait()
        return self.build_blob_name(company_id, document_id, filename) in self.blobs

    async def delete_document(
        self,
        company_id: str,
        document_id: str,
        filename: str,
    ) -> None:
        self.calls.append(("delete", filename))
        await self._wait()
        self.blobs.pop(
            self.build_blob_name(company_id, document_id, filename),
            None,
        )

    async def close(self) -> None:
        self.calls.append(("close", ""))
        if self.close_error is not None:
            raise self.close_error
        self.closed = True


class _TransactionContext:
    def __init__(self, factory: "FakeSessionFactory") -> None:
        self.factory = factory

    async def __aenter__(self):
        self.factory.entered += 1
        return self.factory.session

    async def __aexit__(self, exc_type, _exc_value, _traceback) -> bool:
        if exc_type is None:
            self.factory.committed += 1
        else:
            self.factory.rolled_back += 1
        return False


class FakeSessionFactory:
    """Async transaction context double used by orchestration tests."""

    def __init__(self) -> None:
        self.session = SimpleNamespace()
        self.entered = 0
        self.committed = 0
        self.rolled_back = 0

    def begin(self) -> _TransactionContext:
        return _TransactionContext(self)

    def __call__(self) -> _TransactionContext:
        return _TransactionContext(self)


@pytest.fixture
def fake_storage() -> FakeAsyncStorage:
    return FakeAsyncStorage()


@pytest.fixture
def session_factory() -> FakeSessionFactory:
    return FakeSessionFactory()


@pytest.fixture
def ingestion_bundle(
    fake_storage: FakeAsyncStorage,
    session_factory: FakeSessionFactory,
):
    company_repository = SimpleNamespace(get_by_id=AsyncMock())
    file_repository = SimpleNamespace(
        get_by_id=AsyncMock(),
        create=AsyncMock(),
    )
    document_repository = SimpleNamespace(
        get_by_company_and_file=AsyncMock(),
        create=AsyncMock(),
        update_status=AsyncMock(),
    )
    company_repository.get_by_id.return_value = object()
    document_repository.get_by_company_and_file.return_value = None
    file_repository.get_by_id.return_value = None

    service = DocumentIngestionService(
        session_factory=session_factory,
        company_repository=company_repository,
        file_repository=file_repository,
        document_repository=document_repository,
        storage=fake_storage,
    )

    return SimpleNamespace(
        service=service,
        company_repository=company_repository,
        file_repository=file_repository,
        document_repository=document_repository,
        session_factory=session_factory,
        storage=fake_storage,
    )


@pytest.fixture
def document() -> Document:
    from uuid import uuid4

    return Document(
        company_id=uuid4(),
        filename="fixture.txt",
        file_type="txt",
        source="test",
    )


@pytest.fixture
def file_stream() -> BytesIO:
    return BytesIO(b"RAG01 async migration fixture content")
