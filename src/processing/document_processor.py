from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from models.chunk import Chunk


def load_and_split_documents(
    file_path: str,
    document_id: str,
    company_id: str
):

    loader = PyPDFLoader(file_path)

    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=750,
        chunk_overlap=150
    )

    split_documents = splitter.split_documents(documents)

    chunks = []

    for chunk_index, document in enumerate(split_documents):

        chunk = Chunk(
            document_id=document_id,
            company_id=company_id,
            chunk_text=document.page_content,
            chunk_index=chunk_index,
            page=document.metadata.get("page"),
            source=document.metadata.get("source")
        )

        chunks.append(chunk)

    return chunks