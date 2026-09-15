from retrieval.retrieve import retrieve_docs
from retrieval.bm25 import retrieve_bm25
from retrieval.rrf import reciprocal_rank_fusion
from retrieval.reranker import rerank
from generation.llm import llm


def ask_question(question: str):

    # 1. Dense retrieval
    dense_chunks = retrieve_docs(question)

    # 2. Sparse retrieval using OpenSearch BM25
    bm25_chunks = retrieve_bm25(
        question,
        top_k=20
    )

    # 3. Combine Dense + BM25 rankings
    rrf_chunks = reciprocal_rank_fusion(
        dense_chunks,
        bm25_chunks
    )

    # 4. Keep only the top 5 candidates for reranking
    top_chunks = rrf_chunks[:5]

    # 5. Rerank using the Cross-Encoder
    reranked_chunks = rerank(
        question,
        top_chunks
    )

    # 6. Build context from the final ranked chunks
    context = "\n\n".join(
        chunk.chunk_text
        for chunk in reranked_chunks
    )

    # 7. Build the final prompt
    prompt = f"""
Answer the question only using the context below.

Context:
{context}

Question:
{question}

Answer:
"""

    # 8. Send the prompt to Nemotron
    response = llm.invoke(prompt)

    # 9. Return answer + source information
    return {
        "answer": response.content,
        "sources": reranked_chunks
    }