import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src")
)

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings


embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


vector_store = Chroma(
    persist_directory="vector_store",
    embedding_function=embeddings
)


print("===== CHROMA DIAGNOSTIC =====")

print("Collection name:")
print(vector_store._collection.name)

print("\nNumber of stored records:")
print(vector_store._collection.count())

print("\nStored metadata sample:")

data = vector_store._collection.get(
    limit=3
)

print(data)