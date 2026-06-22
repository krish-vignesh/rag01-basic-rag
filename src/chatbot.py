from retrieve import retrieve_docs
from retrieve import llm

while True:
    question = input("\n How can i help you?") # taking user query as input

    if question.lower() in ["exit", "quit"]:
        print("Goodbye!")
        break
    docs = retrieve_docs(question) # retrieving relevant documents based on user query

    print(f"retrived {len(docs)} documents") # printing number of documents retrieved based on user query

    context = "\n".join(
        
    [d.page_content for d in docs]
    )


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