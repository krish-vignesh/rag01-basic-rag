from pathlib import Path
from io import BytesIO
import sys


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
# Imports
# ---------------------------------------------------------

from src.config.settings import settings
from src.storage.storage import DocumentStorage


# ---------------------------------------------------------
# Initialize storage
# ---------------------------------------------------------

storage = DocumentStorage(
    storage_account_url=settings.azure_storage_account_url,
    container_name=settings.azure_storage_container_name,
)


# ---------------------------------------------------------
# Same blob created by save test
# ---------------------------------------------------------

company_id = "test"
document_id = "storage-test-001"
filename = "storage_test.txt"

expected_content = b"Azure DocumentStorage save test."


# ---------------------------------------------------------
# Download
# ---------------------------------------------------------

reader = storage.download_document(
    company_id=company_id,
    document_id=document_id,
    filename=filename,
)

print("BufferedAzureBlobReader created.")
print(f"Initial position: {reader.tell()}")


# ---------------------------------------------------------
# Read content
# ---------------------------------------------------------

try:
    content = reader.read()
finally:
    reader.close()


print(f"Downloaded bytes: {len(content)}")
print(f"Content: {content.decode()}")


# ---------------------------------------------------------
# Verify
# ---------------------------------------------------------

if content != expected_content:
    raise RuntimeError("Downloaded content does not match uploaded content.")


print("\n--- Download Test Passed ---")