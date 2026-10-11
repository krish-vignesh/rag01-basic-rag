
from io import BytesIO

from src.services.file_identity import calculate_stream_hash


def run_test():
    content = b"RAG01 ingestion test"

    stream = BytesIO(content)

    stream.seek(5)
    original_position = stream.tell()

    first_hash = calculate_stream_hash(stream)

    print("Hash length is 64:", len(first_hash) == 64)
    print("Original position restored:", stream.tell() == original_position)

    second_hash = calculate_stream_hash(BytesIO(content))

    print("Same content gives same hash:", first_hash == second_hash)

    different_hash = calculate_stream_hash(BytesIO(b"different content"))

    print("Different content gives different hash:", first_hash != different_hash)


if __name__ == "__main__":
    run_test()
