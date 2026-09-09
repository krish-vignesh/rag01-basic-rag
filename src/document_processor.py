from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

def load_and_split_documents():

    loader = PyPDFLoader(
    "data/NovaTech_HR_Policy_Handbook.pdf"
    )

    documents = loader.load() #NOTE: loading the documents 

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=750, #chuck size
        chunk_overlap=150 #Overlapping 
        ) #NOTE: Spliting parameters 
    
    chunks = splitter.split_documents(documents)#NOTE: Actually splitting the documents 

    return chunks #!return only the Chunks, all other things are done iternally