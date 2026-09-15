import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src")
)

from models.chunk import Chunk
from retrieval.reranker import rerank


chunk_1 = Chunk(
    document_id="DOC-001",
    company_id="COMPANY-001",
    chunk_text="Employees receive 20 days of annual leave every year.",
    chunk_index=0,
    page=1,
    source="HR_Policy_Handbook.pdf"
)

chunk_2 = Chunk(
    document_id="DOC-001",
    company_id="COMPANY-001",
    chunk_text="Employees can work remotely up to three days per week.",
    chunk_index=1,
    page=5,
    source="HR_Policy_Handbook.pdf"
)

chunk_3 = Chunk(
    document_id="DOC-001",
    company_id="COMPANY-001",
    chunk_text="Employees receive sick leave according to company policy.",
    chunk_index=2,
    page=3,
    source="HR_Policy_Handbook.pdf"
)


chunks = [
    chunk_2,
    chunk_3,
    chunk_1
]


question = "How many days of annual leave do employees receive?"


top_chunks = rerank(
    question=question,
    chunks=chunks
)


print("\n===== RERANKED RESULTS =====\n")

for rank, chunk in enumerate(top_chunks, start=1):

    print(f"Rank: {rank}")
    print(f"Chunk ID: {chunk.chunk_id}")
    print(f"Document ID: {chunk.document_id}")
    print(f"Company ID: {chunk.company_id}")
    print(f"Text: {chunk.chunk_text}")
    print(f"Page: {chunk.page}")
    print(f"Source: {chunk.source}")
    print()