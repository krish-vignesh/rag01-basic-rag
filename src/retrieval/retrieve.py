from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from models.chunk import Chunk


embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


vector_store = Chroma(
    persist_directory="vector_store",
    embedding_function=embeddings
)


retriever = vector_store.as_retriever(
    search_type="mmr",
    search_kwargs={"k": 20}
)


def retrieve_docs(question):

    docs = retriever.invoke(question)

    chunks = []

    for doc in docs:

        chunk = Chunk(
            chunk_id=doc.metadata["chunk_id"],
            document_id=doc.metadata["document_id"],
            company_id=doc.metadata["company_id"],
            chunk_text=doc.page_content,
            chunk_index=doc.metadata["chunk_index"],
            page=doc.metadata.get("page"),
            source=doc.metadata.get("source")
        )

        chunks.append(chunk)

    return chunks




