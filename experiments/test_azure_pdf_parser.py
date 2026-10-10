from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from langchain_core.documents.base import Blob
from langchain_community.document_loaders.parsers import PyPDFParser


STORAGE_ACCOUNT_NAME = "hybridragstorage2026"
CONTAINER_NAME = "documents"

# Put the exact blob name of one PDF already stored in Azure here.
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


print("Connecting to Azure Blob...")
print(f"Blob: {BLOB_NAME}")

download_stream = blob_client.download_blob()

print()
print("Azure download object:")
print(type(download_stream))

print()
print("Testing Azure stream access...")

first_chunk = next(download_stream.chunks())

print(f"First chunk type: {type(first_chunk)}")
print(f"First chunk size: {len(first_chunk):,} bytes")

print()
print("Creating LangChain Blob from first chunk...")

langchain_blob = Blob.from_data(
    first_chunk,
    mime_type="application/pdf",
)

print(f"LangChain Blob created: {langchain_blob}")

print()
print("Testing PyPDFParser...")

parser = PyPDFParser()

documents = list(
    parser.lazy_parse(langchain_blob)
)

print()
print(f"Documents parsed: {len(documents)}")

if documents:
    print()
    print("First document:")
    print(documents[0].page_content[:500])
    print()
    print("Metadata:")
    print(documents[0].metadata)