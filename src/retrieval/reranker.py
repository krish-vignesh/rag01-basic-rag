from sentence_transformers import CrossEncoder

from models.chunk import Chunk


model = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)


def rerank(
        question: str,
        chunks: list[Chunk] #underneath chunk there are attributes like chunk_id, document_id, company_id, chunk_text, chunk_index, page, source
):

    pairs = [
        [question, chunk.chunk_text]
        for chunk in chunks
    ]

    scores = model.predict(pairs)

    chunk_scores = list(
        zip(chunks, scores)
    )

    reranked_chunks = sorted(
        chunk_scores,
        key=lambda x: x[1],
        reverse=True
    )

    top_chunks = [
        chunk
        for chunk, score in reranked_chunks[:5]
    ]

    return top_chunks

