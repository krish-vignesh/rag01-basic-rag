from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama

embeddings = HuggingFaceEmbeddings(
    model_name = "sentence-transformers/all-miniLM-L6-v2"
)  #used to convert user query into vector representation

llm = ChatOllama(
    model = "llama3.2"
)

vector_store = Chroma(
    persist_directory = "vector_store", #directory where vector store is saved
    embedding_function = embeddings
)

retriever = vector_store.as_retriever(
    search_type="mmr",
    search_kwargs={"k": 4}  # number of relevant documents to retrieve based on user query
)  # retriever to retrieve relevant documents from vector store based on user query

def retrieve_docs(question):
    docs = retriever.invoke(question)  # retrieving relevant documents based on user query
    return docs




