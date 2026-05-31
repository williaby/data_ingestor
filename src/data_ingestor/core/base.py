"""Base classes and interfaces for document processing."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, cast

from data_ingestor.core.models import Document, DocumentFormat, ParserResult


class BaseParser(ABC):
    """Abstract base class for document parsers.

    Args:
        config (dict[str, Any] | None): Optional configuration dictionary for parser-specific settings.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.name = self.__class__.__name__

    @abstractmethod
    def supports_format(self, document_format: DocumentFormat) -> bool:
        """Check if this parser supports the given document format.

        Args:
            document_format (DocumentFormat): The format to check.

        Returns:
            bool: True if format is supported, False otherwise.
        """

    @abstractmethod
    def parse(self, document: Document) -> ParserResult:
        """Parse a document and extract structured content.

        # #CRITICAL: External Resources: Assumes document source is accessible
        # #VERIFY: Must validate file accessibility and handle network failures

        # #CRITICAL: Memory Management: Large documents can exhaust memory
        # #VERIFY: Implement streaming or chunked processing for large files

        Args:
            document (Document): Document to parse.

        Returns:
            ParserResult: Parser result with extracted elements and metadata.

        Raises:
            ParserError: If parsing fails.
            UnsupportedFormatError: If format is not supported.
        """

    @abstractmethod
    def health_check(self) -> bool:
        """Check if parser is healthy and operational.

        # #ASSUME: Parser Health: Assumes health check accurately reflects parser state
        # #VERIFY: Should test actual parsing capability, not just initialization

        Returns:
            bool: True if parser is healthy, False otherwise.
        """

    def validate_document(self, document: Document) -> bool:
        """Validate that document can be processed by this parser.

        # #CRITICAL: Data Integrity: Assumes document validation prevents processing failures
        # #VERIFY: Must validate file format, size limits, and accessibility

        Args:
            document (Document): Document to validate.

        Returns:
            bool: True if document is valid, False otherwise.
        """
        # Check format support
        if not self.supports_format(document.format):
            return False

        # Check source exists
        # #CRITICAL: External Resources: File existence check has race condition
        # #VERIFY: Must handle file deletion between check and processing
        if document.source_path:
            path = Path(document.source_path)
            if not path.exists() or not path.is_file():
                return False

        # Check file size if configured
        max_size = self.config.get("max_file_size_mb")
        if max_size and document.source_path:
            path = Path(document.source_path)
            size_mb = path.stat().st_size / (1024 * 1024)
            if size_mb > max_size:
                return False

        return True

    def get_priority(self) -> int:
        """Get parser priority (lower = higher priority).

        Returns:
            int: Priority value (default: 100).
        """
        return cast(int, self.config.get("priority", 100))
