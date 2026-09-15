from models.document import Document
from storage.storage import LocalStorage

from processing.document_processor import load_and_split_documents
from indexing.bm25_index import build_bm25_index
from indexing.chroma import build_chroma_index


def ingest_document(
    source_file: str,
    company_id: str,
    filename: str
):

    document = Document(
        company_id=company_id,
        filename=filename,
        file_type="pdf",
        version=1,
        source=source_file
    )

    storage = LocalStorage(
        base_path="storage"
    )

    stored_file = storage.save(
        source_file=source_file,
        company_id=company_id,
        document_id=document.document_id,
        filename=filename
    )

    chunks = load_and_split_documents(
        file_path=str(stored_file),
        document_id=document.document_id,
        company_id=company_id
    )

    bm25_index = build_bm25_index(chunks)

    vector_store = build_chroma_index(chunks)

    return {
        "document": document,
        "chunks": chunks,
        "bm25_index": bm25_index,
        "vector_store": vector_store
    }
#This is the main function that orchestrates the ingestion of a document
#  It takes the source file path, company ID, and filename as inputs.
#  It creates a Document object, saves the file to local storage
#  splits the document into chunks
#  builds a BM25 index and a Chroma vector store for the chunks
#  and returns all these components in a dictionary.
#it uses the Document model to create a new document instance
#  LocalStorage to save the file, load_and_split_documents to split the document into chunks
#  build_bm25_index to create a BM25 index
#  and build_chroma_index to create a Chroma vector store.