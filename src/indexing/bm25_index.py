from rank_bm25 import BM25Okapi

def build_bm25_index(chunks):
    texts = [chunk.chunk_text for chunk in chunks]

    tokenized_corpus = [
        text.lower().split()
        for text in texts
    ]

    bm25 = BM25Okapi(tokenized_corpus)

    return bm25


