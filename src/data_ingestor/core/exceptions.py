"""Custom exceptions for the data ingestion pipeline."""

from typing import Any


class DataIngestorError(Exception):
    """Base exception for all data ingestor errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        """Initialize the exception with a message and optional details.

        Args:
            message: Human-readable error message
            details: Optional dictionary with additional error context
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ParserError(DataIngestorError):
    """Exception raised when document parsing fails."""

    def __init__(
        self,
        message: str,
        parser_name: str,
        document_path: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize parser error with context.

        Args:
            message: Human-readable error message
            parser_name: Name of the parser that failed
            document_path: Optional path to the document being parsed
            details: Optional dictionary with additional error context
        """
        super().__init__(message, details)
        self.parser_name = parser_name
        self.document_path = document_path


class UnsupportedFormatError(DataIngestorError):
    """Exception raised when document format is not supported."""

    def __init__(
        self,
        format_detected: str | None,
        file_extension: str | None = None,
        mime_type: str | None = None,
    ) -> None:
        """Initialize unsupported format error.

        Args:
            format_detected: The format that was detected (if any)
            file_extension: File extension of the document
            mime_type: MIME type of the document
        """
        message = f"Unsupported document format: {format_detected or 'unknown'}"
        details = {"file_extension": file_extension, "mime_type": mime_type}
        super().__init__(message, details)
        self.format_detected = format_detected


class QualityCheckError(DataIngestorError):
    """Exception raised when quality check fails below threshold."""

    def __init__(
        self,
        quality_score: float,
        threshold: float,
        document_id: str | None = None,
        failed_checks: list[str] | None = None,
    ) -> None:
        """Initialize quality check error.

        Args:
            quality_score: The quality score achieved
            threshold: The required threshold
            document_id: Optional document identifier
            failed_checks: List of failed quality check names
        """
        message = f"Quality check failed: score {quality_score} below threshold {threshold}"
        details = {"quality_score": quality_score, "threshold": threshold, "failed_checks": failed_checks or []}
        super().__init__(message, details)
        self.quality_score = quality_score
        self.threshold = threshold
        self.document_id = document_id


class StorageError(DataIngestorError):
    """Exception raised when storage operation fails."""

    pass


class ChunkingError(DataIngestorError):
    """Exception raised when document chunking fails."""

    pass
