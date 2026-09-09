from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from document_processor import load_and_split_documents

embeddings = HuggingFaceEmbeddings(
    model_name = "sentence-transformers/all-miniLM-L6-v2"

)  #NOTE:embedding model that convert text into vector representation

chunks = load_and_split_documents()

vector_store = Chroma.from_documents(
    documents = chunks, #NOTE:documents to be stored in vector store
    embedding = embeddings,
    persist_directory = "vector_store"  #NOTE:directory where vector store will be saved and now stored in v1    
) #NOTE:creating vector store from documents and embedding model 

print("Vector store created and persisted successfully!")




print(len(chunks)) 
print(chunks[0].metadata) 