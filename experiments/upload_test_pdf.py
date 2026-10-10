from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.storage.blob import ContentSettings


STORAGE_ACCOUNT_NAME = "hybridragstorage2026"
CONTAINER_NAME = "documents"

LOCAL_FILE = Path("data/NovaTech_HR_Policy_Handbook.pdf")

BLOB_NAME = "test/NovaTech_HR_Policy_Handbook.pdf"


account_url = (
    f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
)

credential = DefaultAzureCredential()

blob_service_client = BlobServiceClient(
    account_url=account_url,
    credential=credential,
)

container_client = blob_service_client.get_container_client(
    CONTAINER_NAME
)

blob_client = container_client.get_blob_client(
    BLOB_NAME
)


print("Uploading test PDF to Azure...")

with LOCAL_FILE.open("rb") as file:
    blob_client.upload_blob(
        file,
        overwrite=True,
        content_settings=ContentSettings(
            content_type="application/pdf"
        ),
    )

print("Upload successful.")
print(f"Container: {CONTAINER_NAME}")
print(f"Blob: {BLOB_NAME}")