def reciprocal_rank_fusion(
        dense_docs,
        sparse_docs,
        k=60
):

    doc_map = {}
    rrf_scores = {}

    for rank, doc in enumerate(dense_docs, start=1): #enumerate gives us the index and the document, starting from 1

        doc_id = doc.chunk_id

        doc_map[doc_id] = doc

        rrf_score = 1 / (k + rank)

        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + rrf_score

    for rank, doc in enumerate(sparse_docs, start=1):

        doc_id = doc.chunk_id

        doc_map[doc_id] = doc

        rrf_score = 1 / (k + rank)

        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + rrf_score

    sorted_scores = sorted(
        rrf_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    hybrid_docs = [
        doc_map[doc_id]
        for doc_id, _ in sorted_scores
    ]

    return hybrid_docs