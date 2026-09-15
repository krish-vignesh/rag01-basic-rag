from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from models.chunk import Chunk


embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


def build_chroma_index(chunks):

    documents = [
        Document(
            page_content=chunk.chunk_text,
            metadata={
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "company_id": chunk.company_id,
                "chunk_index": chunk.chunk_index,
                "page": chunk.page,
                "source": chunk.source
            }
        )
        for chunk in chunks
    ]

    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        ids=[chunk.chunk_id for chunk in chunks],
        persist_directory="vector_store"
    )

    return vector_store