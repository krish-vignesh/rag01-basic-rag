import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src")
)

from processing.document_processor import load_and_split_documents
from indexing.bm25_index import build_bm25_index
from retrieval.bm25 import retrieve_bm25
from retrieval.retrieve import retrieve_docs
from retrieval.rrf import reciprocal_rank_fusion


question = "What is the annual leave policy?"


chunks = load_and_split_documents(
    file_path="test_storage/novatech/test-document-001/HR_Policy_Handbook.pdf",
    document_id="DOC-001",
    company_id="COMPANY-001"
)


bm25_index = build_bm25_index(chunks)


dense_results = retrieve_docs(question)


sparse_results = retrieve_bm25(
    question=question,
    bm25=bm25_index,
    chunks=chunks
)


hybrid_results = reciprocal_rank_fusion(
    dense_docs=dense_results,
    sparse_docs=sparse_results
)


print("\n===== DENSE RESULTS =====")
print("Number of results:", len(dense_results))

for rank, chunk in enumerate(dense_results, start=1):
    print(
        rank,
        chunk.chunk_id,
        chunk.chunk_text[:100]
    )


print("\n===== BM25 RESULTS =====")
print("Number of results:", len(sparse_results))

for rank, chunk in enumerate(sparse_results, start=1):
    print(
        rank,
        chunk.chunk_id,
        chunk.chunk_text[:100]
    )


print("\n===== RRF RESULTS =====")
print("Number of results:", len(hybrid_results))

for rank, chunk in enumerate(hybrid_results, start=1):
    print(
        rank,
        chunk.chunk_id,
        chunk.chunk_text[:100]
    )