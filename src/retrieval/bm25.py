import numpy as np


def retrieve_bm25(question, bm25, chunks, top_k=20):
    tokenized_query = question.lower().split()

    scores = bm25.get_scores(tokenized_query)

    ranked_indices = np.argsort(scores)[::-1]

    top_indices = ranked_indices[:top_k]

    top_chunks = [chunks[i] for i in top_indices]

    return top_chunks