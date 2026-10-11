import hashlib

def calculate_file_hash(file_path: str) -> str:
    """
    Calculate the SHA256 hash of a file.

    :param file_path: Path to the file.
    :return: SHA256 hash of the file as a hexadecimal string.
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as file:
        # Read and update hash string value in blocks of 4K
       while chunk := file.read(1024*1024):  # Read in 1MB chunks
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()


from typing import BinaryIO


def calculate_stream_hash(stream: BinaryIO) -> str:
    """
    Calculate the SHA-256 hash of a binary stream.

    Reads the stream in bounded chunks and restores its
    original position before returning.
    """
    original_position = stream.tell()
    sha256_hash = hashlib.sha256()

    try:
        stream.seek(0)

        while chunk := stream.read(1024 * 1024):
            sha256_hash.update(chunk)

        return sha256_hash.hexdigest()

    finally:
        stream.seek(original_position)



#sha 256 is deterministic, meaning that the same input will always produce the same output.
#  This makes it suitable for verifying file integrity and detecting changes.