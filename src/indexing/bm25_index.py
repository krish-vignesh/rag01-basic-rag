import os

from dotenv import load_dotenv
from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk


load_dotenv()


def build_bm25_index(chunks):
    password = os.getenv("OPENSEARCH_INITIAL_ADMIN_PASSWORD")

    client = OpenSearch(
        hosts=[{"host": "localhost", "port": 9200}],
        http_auth=("admin", password),
        use_ssl=True, #use_ssl=True, is required for secure connections, but can be set to False for local development or testing purposes.
        verify_certs=False,
    )

    actions = []

    for chunk in chunks:
        actions.append(
            {
                "_index": "rag_chunks",
                "_id": chunk.chunk_id,
                "_source": {
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "company_id": chunk.company_id,
                    "chunk_text": chunk.chunk_text,
                    "chunk_index": chunk.chunk_index,
                    "page": chunk.page,
                    "source": chunk.source,
                },
            }
        )

    success, failed = bulk(
        client,
        actions,
        refresh="wait_for",
    )

    print("Successfully indexed:", success)
    print("List emptied:", failed)

    return client


