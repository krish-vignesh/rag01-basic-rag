import numpy as np
from rank_bm25 import BM25Okapi

from document_processor import load_and_split_documents


chunks = load_and_split_documents()

texts = [chunk.page_content for chunk in chunks]

tokenized_corpus = [
    text.lower().split()
    for text in texts
]

bm25 = BM25Okapi(tokenized_corpus)


def retrieve_bm25(question, top_k=20):
    tokenized_query = question.lower().split()

    scores = bm25.get_scores(tokenized_query)

    ranked_indices = np.argsort(scores)[::-1]

    top_indices = ranked_indices[:top_k]

    top_chunks = [chunks[i] for i in top_indices]

    return top_chunks