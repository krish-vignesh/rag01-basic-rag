
from io import BufferedIOBase
from typing import BinaryIO

from azure.core.exceptions import ResourceExistsError
from azure.core.credentials import TokenCredential
from azure.identity import (
    AzureCliCredential,
    DefaultAzureCredential,
    ManagedIdentityCredential,
)
from azure.storage.blob import (
    BlobClient,
    BlobServiceClient,
    ContentSettings,
)

from src.config.settings import settings


class BufferedAzureBlobReader(BufferedIOBase):
    def __init__(
        self,
        blob_client: BlobClient,
        blob_size: int,
        buffer_size: int = 8 * 1024 * 1024,
    ):
        self.blob_client = blob_client
        self.blob_size = blob_size
        self.buffer_size = buffer_size

        self.position = 0
        self.buffer_start = 0
        self.buffer_end = 0
        self.buffer = b""

        self._reader_closed = False

    def _fill_buffer(self) -> None:
        if self.position >= self.blob_size:
            self.buffer = b""
            self.buffer_start = self.position
            self.buffer_end = self.position
            return

        start = self.position
        length = min(
            self.buffer_size,
            self.blob_size - start,
        )

        download_stream = self.blob_client.download_blob(
            offset=start,
            length=length,
        )

        self.buffer = download_stream.readall()
        self.buffer_start = start
        self.buffer_end = start + len(self.buffer)

    def read(self, size: int = -1) -> bytes:
        if self.closed:
            raise ValueError("I/O operation on closed reader.")

        if size == 0:
            return b""

        if size < 0:
            size = self.blob_size - self.position

        size = min(
            size,
            self.blob_size - self.position,
        )

        result = bytearray()

        while len(result) < size:
            if not (
                self.buffer_start
                <= self.position
                < self.buffer_end
            ):
                self._fill_buffer()

            if self.buffer_end <= self.position:
                break

            buffer_offset = self.position - self.buffer_start
            remaining = size - len(result)
            available = self.buffer_end - self.position

            bytes_to_take = min(
                remaining,
                available,
            )

            result.extend(
                self.buffer[
                    buffer_offset:buffer_offset + bytes_to_take
                ]
            )

            self.position += bytes_to_take

        return bytes(result)

    def seek(
        self,
        offset: int,
        whence: int = 0,
    ) -> int:
        if self.closed:
            raise ValueError("I/O operation on closed reader.")

        if whence == 0:
            new_position = offset
        elif whence == 1:
            new_position = self.position + offset
        elif whence == 2:
            new_position = self.blob_size + offset
        else:
            raise ValueError(
                f"Unsupported whence value: {whence}"
            )

        if new_position < 0:
            raise ValueError(
                "Negative seek position is not allowed."
            )

        self.position = min(
            new_position,
            self.blob_size,
        )

        return self.position

    def tell(self) -> int:
        if self.closed:
            raise ValueError("I/O operation on closed reader.")

        return self.position

    def readable(self) -> bool:
        return not self.closed

    def seekable(self) -> bool:
        return not self.closed

    def close(self) -> None:
        if not self._reader_closed:
            self._reader_closed = True
            self.buffer = b""
            super().close()


class DocumentStorage:
    def __init__(
        self,
        storage_account_url: str,
        container_name: str,
    ):
        credential = self._create_credential()

        self.blob_service_client = BlobServiceClient(
            account_url=storage_account_url,
            credential=credential,
        )

        self.container_client = (
            self.blob_service_client.get_container_client(
                container_name
            )
        )

    @staticmethod
    def _create_credential() -> TokenCredential:
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

    def save_document(
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
            blob_client.upload_blob(
                stream,
                overwrite=False,
                content_settings=content_settings,
            )
        except ResourceExistsError as exc:
            raise FileExistsError(
                f"Document '{blob_name}' already exists."
            ) from exc

    def download_document(
        self,
        company_id: str,
        document_id: str,
        filename: str,
    ) -> BufferedAzureBlobReader:
        blob_name = self._build_blob_name(
            company_id=company_id,
            document_id=document_id,
            filename=filename,
        )

        blob_client = self.container_client.get_blob_client(
            blob_name
        )

        blob_properties = blob_client.get_blob_properties()

        return BufferedAzureBlobReader(
            blob_client=blob_client,
            blob_size=blob_properties.size,
            buffer_size=8 * 1024 * 1024,
        )

    def exists(
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

        return blob_client.exists()

    def delete_document(
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

        blob_client.delete_blob()
