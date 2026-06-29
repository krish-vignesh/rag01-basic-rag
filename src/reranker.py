from sentence_transformers import CrossEncoder

model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")


def rerank(question, chunks):
    pairs= [[question, c] for c in chunks]
    scores=model.predict(pairs)
    chunk_scores = list(zip(chunks, scores))
    reranked_chunks=sorted(
        chunk_scores,
        key= lambda x:x[1],
        reverse=True
    )
    top_chunks= [chunk for chunk, score in reranked_chunks[:5]]
    return top_chunks

