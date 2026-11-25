"""Verification of async SQLAlchemy configuration and repository boundaries."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from src.database import AsyncSessionFactory, engine
from src.repositories.company_repository import CompanyRepository
from src.repositories.document_repository import DocumentRepository
from src.repositories.file_repository import FileRepository


def test_async_engine_and_session_factory_configuration() -> None:
    assert isinstance(engine, AsyncEngine)
    assert engine.url.drivername == "postgresql+psycopg"
    assert engine.pool._pre_ping is True
    assert AsyncSessionFactory.class_ is AsyncSession
    assert AsyncSessionFactory.kw["bind"] is engine
    assert AsyncSessionFactory.kw["expire_on_commit"] is False


@pytest.mark.asyncio
async def test_company_repository_awaits_execution_and_flush() -> None:
    session = Mock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.add = Mock()

    result = Mock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    repository = CompanyRepository()
    company = await repository.create(session, "Async Test Company")
    found = await repository.get_by_id(session, uuid4())

    assert company.company_name == "Async Test Company"
    assert found is None
    session.add.assert_called_once()
    session.flush.assert_awaited_once()
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_file_and_document_repositories_await_operations() -> None:
    session = Mock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.add = Mock()

    result = Mock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    file_repository = FileRepository()
    document_repository = DocumentRepository()

    file_record = await file_repository.create(session, "a" * 64)
    document = await document_repository.create(
        session=session,
        document_id=uuid4(),
        company_id=uuid4(),
        file_id=file_record.file_id,
        filename="test.txt",
        file_type="txt",
        blob_name="company/document/test.txt",
    )
    missing = await document_repository.get_by_id(session, uuid4())

    assert document.status == "pending"
    assert missing is None
    assert session.flush.await_count == 2
    assert session.execute.await_count == 1
