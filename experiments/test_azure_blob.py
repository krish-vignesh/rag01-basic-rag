from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient


STORAGE_ACCOUNT_NAME = "hybridragstorage2026"
CONTAINER_NAME = "documents"

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

print("Azure authentication successful.")
print(f"Storage account: {STORAGE_ACCOUNT_NAME}")
print(f"Container: {CONTAINER_NAME}")

for blob in container_client.list_blobs():
    print(f"Blob: {blob.name}")