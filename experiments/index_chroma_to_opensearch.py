import os

from dotenv import load_dotenv
from opensearchpy import OpenSearch


load_dotenv()

password = os.getenv("OPENSEARCH_INITIAL_ADMIN_PASSWORD")

client = OpenSearch(
    hosts=[{"host": "localhost", "port": 9200}],
    http_auth=("admin", password),
    use_ssl=True,
    verify_certs=False,
)


if client.ping():
    print("OpenSearch connection successful!")
else:
    print("OpenSearch connection failed!")


from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings


embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

vector_store = Chroma(
    persist_directory="vector_store",
    embedding_function=embeddings
)

data = vector_store.get()

print("Number of Chroma records:", len(data["ids"]))
print("First chunk ID:", data["ids"][0])
print("First chunk text:", data["documents"][0][:200])
print("First chunk metadata:", data["metadatas"][0])


from opensearchpy.helpers import bulk


actions = []

for chunk_id, document, metadata in zip(
    data["ids"],
    data["documents"],
    data["metadatas"]
):
    actions.append(
        {
            "_index": "rag_chunks",
            "_id": chunk_id,
            "_source": {
                "chunk_id": metadata["chunk_id"],
                "document_id": metadata["document_id"],
                "company_id": metadata["company_id"],
                "chunk_text": document,
                "chunk_index": metadata["chunk_index"],
                "page": metadata["page"],
                "source": metadata["source"],
            },
        }
    )


success, failed = bulk(client, actions)

print("Successfully indexed:", success)
print("Failed:", failed)