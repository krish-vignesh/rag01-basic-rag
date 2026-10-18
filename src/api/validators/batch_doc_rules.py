
from fastapi import HTTPException, UploadFile, status

from src.api.validators.documents import (
    MAX_FILE_SIZE_BYTES,
    get_upload_file_size,
)


MAX_BATCH_FILES = 5
MAX_BATCH_SIZE_BYTES = 64 * 1024 * 1024


def validate_batch_upload(files: list[UploadFile]) -> None:
    """Reject batches that violate the count or size limits."""

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one file is required.",
        )

    if len(files) > MAX_BATCH_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A maximum of {MAX_BATCH_FILES} files is allowed per batch.",
        )

    total_size = 0

    for file in files:
        file_size = get_upload_file_size(file)

        if file_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"File '{file.filename}' exceeds the maximum "
                    "individual file size of 32 MiB."
                ),
            )

        total_size += file_size

    if total_size > MAX_BATCH_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="The combined size of all files must not exceed 64 MiB.",
        )
