import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from retrieval.bm25 import retrieve_bm25


question = "What is the annual leave policy?"

chunks = retrieve_bm25(
    question,
    top_k=5
)

print("\nBM25 Results:")
print("-" * 60)

for i, chunk in enumerate(chunks, start=1):
    print(f"\nRank: {i}")
    print(f"Chunk ID: {chunk.chunk_id}")
    print(f"Page: {chunk.page}")
    print(f"Text: {chunk.chunk_text[:300]}")