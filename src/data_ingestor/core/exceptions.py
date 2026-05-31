"""Custom exceptions for the data ingestion pipeline."""

from typing import Any


class DataIngestorError(Exception):
    """Base exception for all data ingestor errors.

    Args:
        message (str): Human-readable error message.
        details (dict[str, Any] | None): Optional dictionary with additional error context.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ParserError(DataIngestorError):
    """Exception raised when document parsing fails.

    Args:
        message (str): Human-readable error message.
        parser_name (str): Name of the parser that failed.
        document_path (str | None): Optional path to the document being parsed.
        details (dict[str, Any] | None): Optional dictionary with additional error context.
    """

    def __init__(
        self,
        message: str,
        parser_name: str,
        document_path: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.parser_name = parser_name
        self.document_path = document_path


class UnsupportedFormatError(DataIngestorError):
    """Exception raised when document format is not supported.

    Args:
        format_detected (str | None): The format that was detected (if any).
        file_extension (str | None): File extension of the document.
        mime_type (str | None): MIME type of the document.
    """

    def __init__(
        self,
        format_detected: str | None,
        file_extension: str | None = None,
        mime_type: str | None = None,
    ) -> None:
        message = f"Unsupported document format: {format_detected or 'unknown'}"
        details = {"file_extension": file_extension, "mime_type": mime_type}
        super().__init__(message, details)
        self.format_detected = format_detected


class QualityCheckError(DataIngestorError):
    """Exception raised when quality check fails below threshold.

    Args:
        quality_score (float): The quality score achieved.
        threshold (float): The required threshold.
        document_id (str | None): Optional document identifier.
        failed_checks (list[str] | None): List of failed quality check names.
    """

    def __init__(
        self,
        quality_score: float,
        threshold: float,
        document_id: str | None = None,
        failed_checks: list[str] | None = None,
    ) -> None:
        message = f"Quality check failed: score {quality_score} below threshold {threshold}"
        details = {"quality_score": quality_score, "threshold": threshold, "failed_checks": failed_checks or []}
        super().__init__(message, details)
        self.quality_score = quality_score
        self.threshold = threshold
        self.document_id = document_id


class StorageError(DataIngestorError):
    """Exception raised when storage operation fails."""



class ChunkingError(DataIngestorError):
    """Exception raised when document chunking fails."""
