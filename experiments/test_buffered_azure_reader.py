from pathlib import Path
import sys
import time

import pypdf
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient


# ---------------------------------------------------------
# 1. Make project root importable
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------
# 2. Project configuration
# ---------------------------------------------------------

from src.config.settings import settings


# ---------------------------------------------------------
# 3. Buffered Azure Blob Reader
# ---------------------------------------------------------

class BufferedAzureBlobReader:
    def __init__(
        self,
        blob_client,
        buffer_size: int = 8 * 1024 * 1024,
    ):
        # Azure Blob client used to retrieve data.
        self.blob_client = blob_client

        # Maximum amount of data held in memory.
        # 8 MB = 8 * 1024 * 1024 bytes.
        self.buffer_size = buffer_size

        # Logical position of the file pointer.
        self.position = 0

        # Start and end positions of the current buffer.
        self.buffer_start = 0
        self.buffer_end = 0

        # Actual bytes currently held in memory.
        self.buffer = b""

    def _fill_buffer(self):
        """
        Fetch a new range of bytes from Azure Blob Storage.
        """

        # Start fetching from the current logical position.
        start = self.position

        # Ask Azure for one buffer-sized range.
        stream = self.blob_client.download_blob(
            offset=start,
            length=self.buffer_size,
        )

        # Read that range into memory.
        self.buffer = stream.readall()

        # Record the range currently held in memory.
        self.buffer_start = start
        self.buffer_end = start + len(self.buffer)

        print(
            f"Azure request: "
            f"bytes {self.buffer_start} -> {self.buffer_end}"
        )

    def read(self, size: int = -1) -> bytes:
        """
        Read bytes from the current file position.

        The method can cross multiple buffer boundaries.
        """

        # -------------------------------------------------
        # Read everything remaining.
        # -------------------------------------------------

        if size == -1:

            stream = self.blob_client.download_blob(
                offset=self.position
            )

            data = stream.readall()

            self.position += len(data)

            return data

        # -------------------------------------------------
        # Nothing requested.
        # -------------------------------------------------

        if size == 0:
            return b""

        remaining = size

        # bytearray lets us efficiently build the final result.
        result = bytearray()

        # -------------------------------------------------
        # Continue until we have returned all requested
        # bytes or reached the end of the blob.
        # -------------------------------------------------

        while remaining > 0:

            # If current position is outside our buffer,
            # fetch a new range from Azure.
            if not (
                self.buffer_start
                <= self.position
                < self.buffer_end
            ):
                self._fill_buffer()

            # Azure returned no data.
            # We have reached the end of the blob.
            if self.buffer_end <= self.position:
                break

            # Position relative to the current buffer.
            buffer_offset = (
                self.position - self.buffer_start
            )

            # Number of bytes available from the current
            # position until the end of this buffer.
            available = (
                self.buffer_end - self.position
            )

            # Don't read more than the caller requested.
            bytes_to_read = min(
                remaining,
                available,
            )

            # Copy bytes from the in-memory buffer.
            result.extend(
                self.buffer[
                    buffer_offset:
                    buffer_offset + bytes_to_read
                ]
            )

            # Advance logical position.
            self.position += bytes_to_read

            # Reduce remaining requested bytes.
            remaining -= bytes_to_read

        return bytes(result)

    def seek(
        self,
        offset: int,
        whence: int = 0,
    ):
        """
        Move the logical file position.

        whence:
            0 = beginning of file
            1 = current position
            2 = end of file
        """

        if whence == 0:

            new_position = offset

        elif whence == 1:

            new_position = self.position + offset

        elif whence == 2:

            properties = self.blob_client.get_blob_properties()

            new_position = properties.size + offset

        else:

            raise ValueError(
                "whence must be 0, 1, or 2"
            )

        if new_position < 0:
            raise ValueError(
                "Cannot seek before the beginning "
                "of the blob."
            )

        self.position = new_position

        return self.position

    def tell(self) -> int:
        """
        Return the current logical file position.
        """

        return self.position

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True


# ---------------------------------------------------------
# 4. Create Azure authentication
# ---------------------------------------------------------

credential = DefaultAzureCredential()


# ---------------------------------------------------------
# 5. Create Blob Service Client
# ---------------------------------------------------------

blob_service_client = BlobServiceClient(
    account_url=settings.azure_storage_account_url,
    credential=credential,
)


# ---------------------------------------------------------
# 6. Create container client
# ---------------------------------------------------------

container_client = blob_service_client.get_container_client(
    settings.azure_storage_container_name
)


# ---------------------------------------------------------
# 7. Get the test PDF blob
# ---------------------------------------------------------

blob_client = container_client.get_blob_client(
    settings.azure_test_blob_name
)


# ---------------------------------------------------------
# 8. Check blob metadata
# ---------------------------------------------------------

properties = blob_client.get_blob_properties()

print("\n--- Blob Information ---")

print(f"Blob: {settings.azure_test_blob_name}")
print(f"Blob size: {properties.size:,} bytes")
print(
    f"Blob size: "
    f"{properties.size / (1024 * 1024):.4f} MB"
)


# ---------------------------------------------------------
# 9. Create buffered reader
# ---------------------------------------------------------

reader = BufferedAzureBlobReader(
    blob_client=blob_client,
    buffer_size=8 * 1024 * 1024,
)


# ---------------------------------------------------------
# 10. PDF parsing test
# ---------------------------------------------------------

print("\n--- PDF Parsing Test ---")

start_time = time.perf_counter()

# pypdf receives our Azure-backed file-like reader.
pdf_reader = pypdf.PdfReader(reader)

page_count = len(pdf_reader.pages)

parsing_time = time.perf_counter() - start_time

print(f"Pages: {page_count}")
print(
    f"Parser initialization time: "
    f"{parsing_time:.4f} seconds"
)


# ---------------------------------------------------------
# 11. Extract text from first page
# ---------------------------------------------------------

print("\n--- First Page Extraction Test ---")

start_time = time.perf_counter()

first_page_text = (
    pdf_reader.pages[0].extract_text()
)

extraction_time = time.perf_counter() - start_time

print(
    f"First page characters: "
    f"{len(first_page_text or '')}"
)

print(
    f"First page extraction time: "
    f"{extraction_time:.4f} seconds"
)


# ---------------------------------------------------------
# 12. Show small text preview
# ---------------------------------------------------------

if first_page_text:

    print("\n--- First Page Preview ---")

    print(
        first_page_text[:500]
    )


# ---------------------------------------------------------
# 13. Final result
# ---------------------------------------------------------

print("\n--- PDF Test Completed ---")

print(
    f"Total measured parser initialization time: "
    f"{parsing_time:.4f} seconds"
)

print(
    f"Total measured first-page extraction time: "
    f"{extraction_time:.4f} seconds"
)