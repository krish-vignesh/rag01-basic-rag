



def reciprocal_rank_fusion(
        dense_docs,
        sparse_docs,
        k=60
):

    doc_map = {}
    rrf_scores = {} #dict to store the scores of each document based on their ranks in dense and sparse retrieval results
    for rank, doc in enumerate(dense_docs, start=1):
        doc_id = doc.page_content  # using the page content of the document as its unique identifier
        doc_map[doc_id] = doc  # storing the document in the doc_map with its unique identifier as the key

        rrf_score = 1 / (k+rank)
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + rrf_score  # adding thereciprocal rank score of the document in the rrf_scores dict

    for rank, doc in enumerate(sparse_docs, start=1):
        doc_id = doc.page_content  # using the page content of the document as its unique identifier
        doc_map[doc_id] = doc  # storing the document in the doc_map with its unique identifier as the key

        rrf_score = 1 / (k+rank)
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + rrf_score  # adding the reciprocal rank score of the document in the rrf_scores dict

        sorted_scores = sorted(
            rrf_scores.items(), #items gives us a pair of (key, value) for each item in the dictionary
            key = lambda x:x[1],
            reverse = True
        )

        hybrid_docs = [doc_map[doc_id] for doc_id, _ in sorted_scores]  # creating a list of documents based on their scores in descending order

        return hybrid_docs  # returning the list of documents sorted by their scores in descending order

        