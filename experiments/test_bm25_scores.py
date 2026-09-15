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


question = "What is the annual leave policy?"

response = client.search(
    index="rag_chunks",
    body={
        "size": 5,
        "query": {
            "match": {
                "chunk_text": question
            }
        }
    }
)


print("\nBM25 Scores:")
print("-" * 60)

for rank, hit in enumerate(response["hits"]["hits"], start=1):
    print(f"\nRank: {rank}")
    print(f"Score: {hit['_score']}")
    print(f"Chunk ID: {hit['_source']['chunk_id']}")
    print(f"Text: {hit['_source']['chunk_text'][:200]}")