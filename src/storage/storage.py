from typing import BinaryIO
from io import BufferedIOBase
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobClient, BlobServiceClient


class BufferedAzureBlobReader(BufferedIOBase):
    def __init__(
        self,
        blob_client: BlobClient,
        blob_size: int,
        buffer_size: int = 8 * 1024 * 1024,
    ):
        # Azure Blob client used to retrieve ranges of the blob.
        self.blob_client = blob_client

        # Total size of the blob in bytes.
        self.blob_size = blob_size

        # Maximum amount of blob data kept in memory at one time.
        self.buffer_size = buffer_size

        # Current logical reading position.
        self.position = 0

        # Start position of the currently cached buffer.
        self.buffer_start = 0

        # End position of the currently cached buffer.
        self.buffer_end = 0

        # The actual bytes currently held in memory.
        self.buffer = b""

        # Indicates whether the reader has been closed.
        self._closed = False

    def _fill_buffer(self) -> None:
        # If the current position is already at the end,
        # there is nothing more to download.
        if self.position >= self.blob_size:
            self.buffer = b""
            self.buffer_start = self.position
            self.buffer_end = self.position
            return

        # Start downloading from the current reading position.
        start = self.position

        # Do not request more bytes than remain in the blob.
        length = min(
            self.buffer_size,
            self.blob_size - start,
        )

        # Ask Azure Blob Storage for only this byte range.
        download_stream = self.blob_client.download_blob(
            offset=start,
            length=length,
        )

        # Read the requested range into memory.
        self.buffer = download_stream.readall()

        # Record where this buffer begins.
        self.buffer_start = start

        # Record where this buffer ends.
        self.buffer_end = start + len(self.buffer)

    def read(self, size: int = -1) -> bytes:
        # Do not allow operations on a closed reader.
        if self._closed:
            raise ValueError("I/O operation on closed reader.")

        # If the caller asks for all remaining bytes,
        # calculate the amount remaining.
        if size < 0:
            size = self.blob_size - self.position

        # Nothing requested means nothing returned.
        if size == 0:
            return b""

        # Do not read beyond the end of the blob.
        size = min(
            size,
            self.blob_size - self.position,
        )

        # Store the pieces collected from one or more buffers.
        result = bytearray()

        # Continue until the requested amount has been collected.
        while len(result) < size:
            # Check whether the current position is outside
            # the currently cached buffer.
            if not (
                self.buffer_start
                <= self.position
                < self.buffer_end
            ):
                self._fill_buffer()

            # Stop if there is no more data available.
            if self.buffer_end <= self.position:
                break

            # Calculate where inside the buffer we should start.
            buffer_offset = (
                self.position - self.buffer_start
            )

            # Calculate how many bytes are still needed.
            remaining = size - len(result)

            # Calculate how many bytes are available
            # inside the current buffer.
            available = self.buffer_end - self.position

            # Take only the amount needed for this read.
            bytes_to_take = min(
                remaining,
                available,
            )

            # Append those bytes to the result.
            result.extend(
                self.buffer[
                    buffer_offset:
                    buffer_offset + bytes_to_take
                ]
            )

            # Move the logical reading position forward.
            self.position += bytes_to_take

        return bytes(result)

    def seek(
        self,
        offset: int,
        whence: int = 0,
    ) -> int:
        # Do not allow operations on a closed reader.
        if self._closed:
            raise ValueError("I/O operation on closed reader.")

        # whence=0 means position from the beginning.
        if whence == 0:
            new_position = offset

        # whence=1 means position relative to current position.
        elif whence == 1:
            new_position = self.position + offset

        # whence=2 means position relative to the end.
        elif whence == 2:
            new_position = self.blob_size + offset

        # Reject unsupported seek modes.
        else:
            raise ValueError(
                f"Unsupported whence value: {whence}"
            )

        # Reject positions before the beginning of the blob.
        if new_position < 0:
            raise ValueError(
                "Negative seek position is not allowed."
            )

        # Allow seeking exactly to the end,
        # but never beyond the end.
        self.position = min(
            new_position,
            self.blob_size,
        )

        return self.position

    def tell(self) -> int:
        # Do not allow operations on a closed reader.
        if self._closed:
            raise ValueError("I/O operation on closed reader.")

        # Return the current logical position.
        return self.position

    def readable(self) -> bool:
        # This object supports reading.
        return not self._closed

    def seekable(self) -> bool:
        # This object supports seeking.
        return not self._closed

    def close(self) -> None:
        # Mark the reader as closed.
        self._closed = True

        # Release the in-memory buffer.
        self.buffer = b""

        # Let the parent class perform its normal close behavior.
        super().close()

    @property
    def closed(self) -> bool:
        # Expose the reader's closed state.
        return self._closed


class DocumentStorage:
    def __init__(
        self,
        storage_account_url: str,
        container_name: str,
    ):
        # Use Microsoft Entra ID credentials instead of storage keys.
        credential = DefaultAzureCredential()

        # Create the client used to communicate with Azure Blob Storage.
        self.blob_service_client = BlobServiceClient(
            account_url=storage_account_url,
            credential=credential,
        )

        # Restrict this storage component to our document container.
        self.container_client = (
            self.blob_service_client.get_container_client(
                container_name
            )
        )

    def _build_blob_name(
        self,
        company_id: str,
        document_id: str,
        filename: str,
    ) -> str:
        # Build a tenant-aware blob name.
        return f"{company_id}/{document_id}/{filename}"

    def save_document(
        self,
        stream: BinaryIO,
        company_id: str,
        document_id: str,
        filename: str,
        content_type: str | None = None,
    ) -> None:
        # Convert our document identity into an Azure blob name.
        blob_name = self._build_blob_name(
            company_id=company_id,
            document_id=document_id,
            filename=filename,
        )

        # Get a client for this specific blob.
        blob_client = self.container_client.get_blob_client(
            blob_name
        )

        # Prevent accidental overwriting of an existing document.
        if blob_client.exists():
            raise FileExistsError(
                f"Document '{blob_name}' already exists."
            )

        # Upload the stream directly to Azure Blob Storage.
        blob_client.upload_blob(
            stream,
            overwrite=False,
            content_type=content_type,
        )

    def download_document(
        self,
        company_id: str,
        document_id: str,
        filename: str,
    ) -> BufferedAzureBlobReader:
        # Recreate the same blob name used during upload.
        blob_name = self._build_blob_name(
            company_id=company_id,
            document_id=document_id,
            filename=filename,
        )

        # Get a client for this specific blob.
        blob_client = self.container_client.get_blob_client(
            blob_name
        )

        # Retrieve blob metadata so the reader knows the
        # total size of the document.
        blob_properties = blob_client.get_blob_properties()

        # Create a buffered reader over the Azure blob.
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
        # Recreate the blob identity.
        blob_name = self._build_blob_name(
            company_id=company_id,
            document_id=document_id,
            filename=filename,
        )

        # Get a client for this specific blob.
        blob_client = self.container_client.get_blob_client(
            blob_name
        )

        # Ask Azure whether the blob exists.
        return blob_client.exists()