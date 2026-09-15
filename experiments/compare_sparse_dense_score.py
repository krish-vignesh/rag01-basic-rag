import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from retrieval.retrieve import retrieve_docs
from retrieval.bm25 import retrieve_bm25


question = "What is the annual leave policy?"

dense_chunks = retrieve_docs(question)

bm25_chunks = retrieve_bm25(
    question,
    top_k=20
)


dense_ids = [chunk.chunk_id for chunk in dense_chunks]
bm25_ids = [chunk.chunk_id for chunk in bm25_chunks]


overlap = set(dense_ids) & set(bm25_ids)


print("\nDense vs BM25")
print("-" * 60)

print("Dense results:", len(dense_ids))
print("BM25 results:", len(bm25_ids))
print("Overlapping chunks:", len(overlap))


print("\nDense Top 10:")
for rank, chunk_id in enumerate(dense_ids[:10], start=1):
    print(f"{rank}. {chunk_id}")


print("\nBM25 Top 10:")
for rank, chunk_id in enumerate(bm25_ids[:10], start=1):
    print(f"{rank}. {chunk_id}")