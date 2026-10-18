
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


class DocumentUploadResponse(BaseModel):
    """Public response returned after a document upload succeeds."""

    model_config = ConfigDict(extra="forbid")

    document_id: str
    filename: str
    company_id: str
    status: str
    message: str = "Document uploaded successfully."


class BatchDocumentUploadResult(BaseModel):
    """Outcome of processing one file in a batch."""

    model_config = ConfigDict(extra="forbid")

    filename: str
    outcome: Literal["success", "failure", "not_processed"]
    document: DocumentUploadResponse | None = None
    error_code: str | None = None
    message: str | None = None

    @model_validator(mode="after")
    def validate_outcome_fields(self):
        """Ensure the fields match the file's outcome."""

        if self.outcome == "success":
            if self.document is None:
                raise ValueError(
                    "A successful result must include document details."
                )

            if self.error_code is not None or self.message is not None:
                raise ValueError(
                    "A successful result cannot contain error details."
                )

        else:
            if self.document is not None:
                raise ValueError(
                    "A non-successful result cannot include document details."
                )

            if not self.error_code or not self.message:
                raise ValueError(
                    "A failed or unprocessed result must include "
                    "an error code and message."
                )

        return self


class BatchDocumentUploadResponse(BaseModel):
    """Summary and individual outcomes of a batch upload."""

    model_config = ConfigDict(extra="forbid")

    total_files: int
    successful_uploads: int
    failed_uploads: int
    not_processed: int
    results: list[BatchDocumentUploadResult]

    @model_validator(mode="after")
    def validate_summary_counts(self):
        """Ensure summary counts match the individual outcomes."""

        if self.total_files != len(self.results):
            raise ValueError(
                "total_files must match the number of results."
            )

        actual_successful = sum(
            result.outcome == "success" for result in self.results
        )
        actual_failed = sum(
            result.outcome == "failure" for result in self.results
        )
        actual_not_processed = sum(
            result.outcome == "not_processed" for result in self.results
        )

        if (
            self.successful_uploads != actual_successful
            or self.failed_uploads != actual_failed
            or self.not_processed != actual_not_processed
        ):
            raise ValueError(
                "Summary counts must match the individual outcomes."
            )

        return self
