import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from retrieval.retrieve import retrieve_docs
from retrieval.bm25 import retrieve_bm25
from retrieval.rrf import reciprocal_rank_fusion


question = "What is the annual leave policy?"


dense_chunks = retrieve_docs(question)

bm25_chunks = retrieve_bm25(
    question,
    top_k=20
)


rrf_chunks = reciprocal_rank_fusion(
    dense_chunks,
    bm25_chunks
)


print("\nRRF Results")
print("-" * 60)

for rank, chunk in enumerate(rrf_chunks[:10], start=1):

    print(f"\nRank: {rank}")
    print(f"Chunk ID: {chunk.chunk_id}")
    print(f"Page: {chunk.page}")
    print(f"Text: {chunk.chunk_text[:250]}")