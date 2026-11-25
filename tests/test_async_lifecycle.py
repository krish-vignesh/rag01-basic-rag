"""Verification of application lifespan ownership and cleanup."""

import asyncio
from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import AsyncMock

import pytest

import src.main as main_module


class FakeStorage:
    instances: ClassVar[list["FakeStorage"]] = []

    def __init__(self, **_kwargs) -> None:
        self.close = AsyncMock()
        self.__class__.instances.append(self)


class FakeService:
    instances: ClassVar[list["FakeService"]] = []

    def __init__(self, **kwargs) -> None:
        self.storage = kwargs["storage"]
        self.__class__.instances.append(self)


@pytest.fixture
def lifecycle_fakes(monkeypatch):
    FakeStorage.instances.clear()
    FakeService.instances.clear()
    engine_dispose = AsyncMock()
    monkeypatch.setattr(main_module, "DocumentStorage", FakeStorage)
    monkeypatch.setattr(main_module, "DocumentIngestionService", FakeService)
    monkeypatch.setattr(
        main_module,
        "engine",
        SimpleNamespace(dispose=engine_dispose),
    )
    return engine_dispose


@pytest.mark.asyncio
async def test_lifespan_initializes_shared_service_and_cleans_up(
    lifecycle_fakes,
) -> None:
    app = SimpleNamespace(state=SimpleNamespace())

    async with main_module.lifespan(app):
        assert app.state.ingestion_service is FakeService.instances[0]
        assert len(FakeStorage.instances) == 1

    FakeStorage.instances[0].close.assert_awaited_once()
    lifecycle_fakes.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_disposes_engine_when_storage_cleanup_fails(
    lifecycle_fakes,
) -> None:
    app = SimpleNamespace(state=SimpleNamespace())

    with pytest.raises(ExceptionGroup) as raised:
        async with main_module.lifespan(app):
            storage = FakeStorage.instances[-1]
            storage.close.side_effect = RuntimeError("storage close failed")
            lifecycle_fakes.side_effect = RuntimeError("engine dispose failed")

    assert len(raised.value.exceptions) == 2
    storage.close.assert_awaited_once()
    lifecycle_fakes.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_preserves_primary_application_exception(
    lifecycle_fakes,
) -> None:
    app = SimpleNamespace(state=SimpleNamespace())

    with pytest.raises(ValueError, match="application failed"):
        async with main_module.lifespan(app):
            raise ValueError("application failed")


@pytest.mark.asyncio
async def test_lifespan_re_raises_cleanup_cancellation(
    lifecycle_fakes,
) -> None:
    app = SimpleNamespace(state=SimpleNamespace())

    async with main_module.lifespan(app):
        pass

    FakeStorage.instances[0].close.side_effect = asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        async with main_module.lifespan(app):
            FakeStorage.instances[-1].close.side_effect = asyncio.CancelledError()

    lifecycle_fakes.assert_awaited()
