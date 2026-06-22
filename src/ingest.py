from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
loader = PyPDFLoader(
    "data/NovaTech_HR_Policy_Handbook.pdf"
)
documents = loader.load()

splitter = RecursiveCharacterTextSplitter(
    chunk_size=750, #chuck size
    chunk_overlap=150 #Overlapping 
    )

chunks = splitter.split_documents(documents)  #splitting into chunks

embeddings = HuggingFaceEmbeddings(
    model_name = "sentence-transformers/all-miniLM-L6-v2"

)  #embedding model that convert text into vector representation

vector_store = Chroma.from_documents(
    documents = chunks, #documents to be stored in vector store
    embedding = embeddings,
    persist_directory = "vector_store"  #directory where vector store will be saved and now stored in v1    
) #creating vector store from documents and embedding model 

print("Vector store created and persisted successfully!")




print(len(chunks))  
print(chunks[0].metadata)