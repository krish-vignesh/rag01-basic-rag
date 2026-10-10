from pathlib import Path
import sys

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


# ---------------------------------------------------------
# Application imports
# ---------------------------------------------------------

from src.config.settings import settings
from src.storage.storage import BufferedAzureBlobReader
from src.processing.document_processor import load_and_split_documents


# ---------------------------------------------------------
# Azure Blob connection
# ---------------------------------------------------------

blob_service_client = BlobServiceClient(
    account_url=settings.azure_storage_account_url,
    credential=DefaultAzureCredential(),
)

container_client = blob_service_client.get_container_client(
    settings.azure_storage_container_name
)


# ---------------------------------------------------------
# Existing test blob
# ---------------------------------------------------------

blob_name = settings.azure_test_blob_name

print(f"Test blob: {blob_name}")


# ---------------------------------------------------------
# Create BlobClient
# ---------------------------------------------------------

blob_client = container_client.get_blob_client(blob_name)

blob_properties = blob_client.get_blob_properties()

print(f"Blob size: {blob_properties.size:,} bytes")


# ---------------------------------------------------------
# Create buffered Azure reader
# ---------------------------------------------------------

reader = BufferedAzureBlobReader(
    blob_client=blob_client,
    blob_size=blob_properties.size,
    buffer_size=8 * 1024 * 1024,
)

print("BufferedAzureBlobReader created.")
print(f"Initial position: {reader.tell()}")


# ---------------------------------------------------------
# Process PDF
# ---------------------------------------------------------

document_id = "azure-reader-test"
company_id = "test"

try:

    chunks = load_and_split_documents(
        file_stream=reader,
        document_id=document_id,
        company_id=company_id,
        source=blob_name,
    )

finally:

    reader.close()


# ---------------------------------------------------------
# Results
# ---------------------------------------------------------

print("\n--- PDF Processing Result ---")

print(f"Total chunks: {len(chunks)}")


if chunks:

    first_chunk = chunks[0]

    print("\n--- First Chunk ---")

    print(f"Chunk ID: {first_chunk.chunk_id}")
    print(f"Document ID: {first_chunk.document_id}")
    print(f"Company ID: {first_chunk.company_id}")
    print(f"Chunk Index: {first_chunk.chunk_index}")
    print(f"Page: {first_chunk.page}")
    print(f"Source: {first_chunk.source}")

    print("\nText:")
    print(first_chunk.chunk_text[:500])


print("\n--- Test Completed ---")