from retrieve import retrieve_docs, extract_chunks
from retrieve import llm
import os
from reranker import rerank 
from dotenv import load_dotenv #! importing load_dotenv to load environment variables from .env file

load_dotenv() #! loading environment variables from .env file
while True:
    question = input("\n How can i help you?") # taking user query as input

    if question.lower() in ["exit", "quit", "over", "enough"]:
        print("Goodbye!")
        break
    docs = retrieve_docs(question) # retrieving relevant documents based on user query

    chunks = extract_chunks(docs) #NOTE: take only the content from the docs not the metadata

    top_chunks = rerank(question, chunks) #!Taking the top chunks with the help of rerank function from raranker.py

    print(f"retrived {len(docs)} documents") # printing number of documents retrieved based on user query

    context = "\n".join(top_chunks)
    print("\n===== Top 5 Re-ranked Chunks Extracted =====")

    


    prompt = f"""
answer the question only using the context below.

context:
{context}

question:
{question}
"""
    response = llm.invoke(prompt) # generating response based on user query and retrieved documents

    print('\nbot:')
    print(response.content)