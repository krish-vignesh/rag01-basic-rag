import asyncio
import logging
import tempfile
from typing import BinaryIO

from azure.core.credentials_async import AsyncTokenCredential
from azure.core.exceptions import ResourceExistsError
from azure.identity.aio import (
    AzureCliCredential,
    DefaultAzureCredential,
    ManagedIdentityCredential,
)
from azure.storage.blob import ContentSettings
from azure.storage.blob.aio import (
    BlobServiceClient,
    ContainerClient,
)

from src.config.settings import settings

logger = logging.getLogger(__name__)

_MAX_CLEANUP_ATTEMPTS = 2


class DocumentStorage:
    def __init__(
        self,
        storage_account_url: str,
        container_name: str,
    ):
        self.credential = self._create_credential()

        self.blob_service_client = BlobServiceClient(
            account_url=storage_account_url,
            credential=self.credential,
        )

        self.container_client: ContainerClient = (
            self.blob_service_client.get_container_client(
                container_name
            )
        )

        self._service_client_closed = False
        self._credential_closed = False

    @staticmethod
    def _create_credential() -> AsyncTokenCredential:
        credential_mode = settings.azure_credential_mode

        if credential_mode == "azure_cli":
            return AzureCliCredential()

        if credential_mode == "managed_identity":
            return ManagedIdentityCredential()

        if credential_mode == "default":
            return DefaultAzureCredential()

        # Normally prevented by the Literal setting in settings.py.
        raise ValueError(
            f"Unsupported Azure credential mode: {credential_mode}"
        )

    def build_blob_name(
        self,
        company_id: str,
        document_id: str,
        filename: str,
    ) -> str:
        """Return the canonical Azure blob name."""
        return self._build_blob_name(
            company_id=company_id,
            document_id=document_id,
            filename=filename,
        )

    def _build_blob_name(
        self,
        company_id: str,
        document_id: str,
        filename: str,
    ) -> str:
        """Keep document objects organized by company and document."""
        return f"{company_id}/{document_id}/{filename}"

    async def save_document(
        self,
        stream: BinaryIO,
        company_id: str,
        document_id: str,
        filename: str,
        content_type: str | None = None,
    ) -> None:
        blob_name = self._build_blob_name(
            company_id=company_id,
            document_id=document_id,
            filename=filename,
        )

        blob_client = self.container_client.get_blob_client(
            blob_name
        )

        content_settings = (
            ContentSettings(content_type=content_type)
            if content_type
            else None
        )

        try:
            # Conditional creation: do not overwrite an existing blob.
            # This avoids a separate existence-check network request.
            await blob_client.upload_blob(
                stream,
                overwrite=False,
                content_settings=content_settings,
            )
        except ResourceExistsError as exc:
            raise FileExistsError(
                f"Document '{blob_name}' already exists."
            ) from exc

    async def download_document(
        self,
        company_id: str,
        document_id: str,
        filename: str,
    ) -> BinaryIO:
        blob_name = self._build_blob_name(
            company_id=company_id,
            document_id=document_id,
            filename=filename,
        )

        blob_client = self.container_client.get_blob_client(
            blob_name
        )

        stream = tempfile.SpooledTemporaryFile(
            max_size=8 * 1024 * 1024,
            mode="w+b",
        )

        try:
            download_stream = await blob_client.download_blob()
            await download_stream.readinto(stream)
            stream.seek(0)
            return stream
        except Exception:
            stream.close()
            raise

    async def exists(
        self,
        company_id: str,
        document_id: str,
        filename: str,
    ) -> bool:
        blob_name = self._build_blob_name(
            company_id=company_id,
            document_id=document_id,
            filename=filename,
        )

        blob_client = self.container_client.get_blob_client(
            blob_name
        )

        return await blob_client.exists()

    async def delete_document(
        self,
        company_id: str,
        document_id: str,
        filename: str,
    ) -> None:
        """Delete one explicitly identified document blob."""
        blob_name = self._build_blob_name(
            company_id=company_id,
            document_id=document_id,
            filename=filename,
        )

        blob_client = self.container_client.get_blob_client(
            blob_name
        )

        await blob_client.delete_blob()

    async def close(self) -> None:
        cleanup_errors: list[Exception] = []
        cleanup_cancellations: list[asyncio.CancelledError] = []

        cleanup_targets = (
            (
                "Azure Blob service client",
                self.blob_service_client.close,
                "_service_client_closed",
            ),
            ("Azure credential", self.credential.close, "_credential_closed"),
        )

        logger.debug("Beginning document storage cleanup.")
        for resource_name, close_operation, closed_flag in cleanup_targets:
            if getattr(self, closed_flag):
                continue

            for attempt in range(1, _MAX_CLEANUP_ATTEMPTS + 1):
                try:
                    await close_operation()
                except asyncio.CancelledError as exc:
                    cleanup_cancellations.append(exc)
                    logger.warning(
                        "%s cleanup was cancelled; the resource remains "
                        "unclosed.",
                        resource_name,
                        exc_info=True,
                    )
                    break
                except Exception as exc:
                    if attempt < _MAX_CLEANUP_ATTEMPTS:
                        logger.warning(
                            "%s cleanup failed; retrying "
                            "(attempt %d/%d).",
                            resource_name,
                            attempt,
                            _MAX_CLEANUP_ATTEMPTS,
                            exc_info=True,
                        )
                    else:
                        cleanup_errors.append(exc)
                        logger.exception(
                            "%s cleanup failed after %d attempts; the "
                            "resource remains unclosed.",
                            resource_name,
                            _MAX_CLEANUP_ATTEMPTS,
                        )
                else:
                    setattr(self, closed_flag, True)
                    logger.debug("%s cleanup succeeded.", resource_name)
                    break

        if cleanup_cancellations:
            for cleanup_error in cleanup_errors:
                logger.error(
                    "Document storage cleanup failed while "
                    "preserving cancellation.",
                    exc_info=(
                        type(cleanup_error),
                        cleanup_error,
                        cleanup_error.__traceback__,
                    ),
                )
            raise cleanup_cancellations[0]

        if cleanup_errors:
            raise ExceptionGroup(
                "Document storage cleanup failed.",
                cleanup_errors,
            )

    async def __aenter__(self) -> "DocumentStorage":
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_value: BaseException | None,
        _traceback: object | None,
    ) -> None:
        del _exc_type, _exc_value, _traceback
        await self.close()