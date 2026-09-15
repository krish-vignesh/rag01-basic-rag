import sys
from pathlib import Path

from transformers import Chunk


sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src")
)

from models.chunk import Chunk
from retrieval.rrf import reciprocal_rank_fusion


chunk_1 = Chunk(
    document_id="DOC-001",
    company_id="COMPANY-001",
    chunk_text="Annual leave policy",
    chunk_index=0
)

chunk_2 = Chunk(
    document_id="DOC-001",
    company_id="COMPANY-001",
    chunk_text="Sick leave policy",
    chunk_index=1
)

chunk_3 = Chunk(
    document_id="DOC-001",
    company_id="COMPANY-001",
    chunk_text="Remote work policy",
    chunk_index=2
)


dense_results = [
    chunk_1,
    chunk_2,
    chunk_3
]


sparse_results = [
    chunk_3,
    chunk_1,
    chunk_2
]


hybrid_results = reciprocal_rank_fusion(
    dense_docs=dense_results,
    sparse_docs=sparse_results
)


for rank, chunk in enumerate(hybrid_results, start=1):

    print(
        rank,
        chunk.chunk_id,
        chunk.chunk_text
    )