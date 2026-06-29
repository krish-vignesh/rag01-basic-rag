from retrieve import retrieve_docs, extract_chunks
from reranker import rerank 

question = "how many sick leave days are provided in a year"

docs = retrieve_docs(question)

chunks = extract_chunks(docs)

reranked_chunks = rerank(question, chunks)

print(reranked_chunks)