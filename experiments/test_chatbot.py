import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chatbot import ask_question


question = "What is the annual leave policy?"

result = ask_question(question)

print("\nAnswer:")
print("-" * 60)
print(result["answer"])

print("\nSources:")
print("-" * 60)

for rank, chunk in enumerate(result["sources"], start=1):
    print(f"\nSource {rank}")
    print(f"Chunk ID: {chunk.chunk_id}")
    print(f"Page: {chunk.page}")
    print(f"Text: {chunk.chunk_text[:200]}")