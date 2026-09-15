import os

from dotenv import load_dotenv
from opensearchpy import OpenSearch

from models.chunk import Chunk


load_dotenv()


def retrieve_bm25(question: str, top_k: int = 20):

    password = os.getenv("OPENSEARCH_INITIAL_ADMIN_PASSWORD")

    client = OpenSearch(
        hosts=[{"host": "localhost", "port": 9200}],
        http_auth=("admin", password),
        use_ssl=True,
        verify_certs=False,
    )

    response = client.search(
        index="rag_chunks",
        body={
            "size": top_k,
            "query": {
                "match": {
                    "chunk_text": question
                }
            }
        }
    )

    chunks = []

    for hit in response["hits"]["hits"]:

        source = hit["_source"]

        chunk = Chunk(
            chunk_id=source["chunk_id"],
            document_id=source["document_id"],
            company_id=source["company_id"],
            chunk_text=source["chunk_text"],
            chunk_index=source["chunk_index"],
            page=source.get("page"),
            source=source.get("source")
        )

        chunks.append(chunk)

    return chunks