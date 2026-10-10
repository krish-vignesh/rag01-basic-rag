from io import BufferedIOBase

import pypdf
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from models.chunk import Chunk


def load_and_split_documents(
    file_stream: BufferedIOBase,
    document_id: str,
    company_id: str,
    source: str | None = None,
):

    # Read the PDF directly from the provided binary stream.
    pdf_reader = pypdf.PdfReader(file_stream)

    # Store each PDF page as a LangChain Document.
    documents = []

    for page_number, page in enumerate(pdf_reader.pages):

        # Extract text from the current PDF page.
        page_text = page.extract_text() or ""

        # Create a LangChain Document for this page.
        document = Document(
            page_content=page_text,
            metadata={
                "page": page_number,
                "source": source,
            },
        )

        documents.append(document)

    # Create the same text splitter used by the previous implementation.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=750,
        chunk_overlap=150,
    )

    # Split the page documents into smaller retrieval chunks.
    split_documents = splitter.split_documents(documents)

    # Convert LangChain Documents into our application's Chunk model.
    chunks = []

    for chunk_index, document in enumerate(split_documents):

        chunk = Chunk(
            document_id=document_id,
            company_id=company_id,
            chunk_text=document.page_content,
            chunk_index=chunk_index,
            page=document.metadata.get("page"),
            source=document.metadata.get("source"),
        )

        chunks.append(chunk)

    return chunks