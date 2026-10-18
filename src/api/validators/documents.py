
from pathlib import Path

from fastapi import HTTPException, UploadFile, status


ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".csv",
    ".md",
    ".txt",
    ".json",
}

MAX_FILE_SIZE_BYTES = 32 * 1024 * 1024


def validate_file_extension(filename: str) -> str:
    """Validate the filename extension and return the normalized file type."""
    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file format.",
        )

    return extension.lstrip(".")


def get_upload_file_size(file: UploadFile) -> int:
    """Return the uploaded file size in bytes without changing its stream position."""
    if file.size is not None:
        return file.size

    stream = file.file
    original_position = None

    try:
        original_position = stream.tell()
        stream.seek(0, 2)
        file_size = stream.tell()
        stream.seek(original_position)
        return file_size

    except (OSError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The size of the uploaded file could not be determined.",
        ) from None

    finally:
        if original_position is not None:
            try:
                stream.seek(original_position)
            except (OSError, ValueError):
                pass


def validate_file_size(file: UploadFile) -> None:
    """Reject a file that exceeds the individual upload size limit."""
    file_size = get_upload_file_size(file)

    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="The file exceeds the maximum individual file size of 32 MiB.",
        )
