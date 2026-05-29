"""Document router for selecting appropriate parsers."""

import contextlib
import hashlib
import logging
from pathlib import Path
from typing import Any

from data_ingestor.core.base import BaseParser
from data_ingestor.core.config import Settings
from data_ingestor.core.exceptions import ParserError, UnsupportedFormatError
from data_ingestor.core.models import Document, DocumentFormat, ParserResult, ProcessingStatus
from data_ingestor.pipeline.pdf_analyzer import PDFDocumentAnalyzer, PDFPreflightResult
from data_ingestor.utils.format_detector import FormatDetector

logger = logging.getLogger(__name__)


class ParserRegistry:
    """Registry for managing document parsers with fallback chains."""

    def __init__(self) -> None:
        """Initialize parser registry."""
        self._parsers: dict[DocumentFormat, list[BaseParser]] = {
            DocumentFormat.PDF: [],
            DocumentFormat.DOCX: [],
            DocumentFormat.HTML: [],
            DocumentFormat.VIDEO: [],
            DocumentFormat.AUDIO: [],
        }

    def register(self, parser: BaseParser, formats: list[DocumentFormat]) -> None:
        """Register a parser for specific formats.

        Args:
            parser: Parser instance to register
            formats: List of formats this parser supports
        """
        for fmt in formats:
            if fmt not in self._parsers:
                self._parsers[fmt] = []
            self._parsers[fmt].append(parser)
            # Sort by priority (lower number = higher priority)
            self._parsers[fmt].sort(key=lambda p: p.get_priority())

        logger.info(f"Registered parser {parser.name} for formats: {[f.value for f in formats]}")

    def get_parsers(self, document_format: DocumentFormat) -> list[BaseParser]:
        """Get parsers for a specific format.

        # #CRITICAL: Parser Availability: Assumes at least one parser registered per format
        # #VERIFY: Must validate parser availability before processing

        Args:
            document_format: Document format to get parsers for

        Returns:
            List of parsers ordered by priority
        """
        return self._parsers.get(document_format, [])

    def get_primary_parser(self, document_format: DocumentFormat) -> BaseParser | None:
        """Get highest priority parser for format.

        Args:
            document_format: Document format

        Returns:
            Primary parser or None if no parsers available
        """
        parsers = self.get_parsers(document_format)
        return parsers[0] if parsers else None

    def health_check(self) -> dict[str, Any]:
        """Check health of all registered parsers.

        Returns:
            Dictionary with health status for each parser
        """
        health_status: dict[str, Any] = {}
        for fmt, parsers in self._parsers.items():
            health_status[fmt.value] = []
            for parser in parsers:
                try:
                    is_healthy = parser.health_check()
                    health_status[fmt.value].append({"name": parser.name, "healthy": is_healthy})
                except Exception as e:
                    health_status[fmt.value].append({"name": parser.name, "healthy": False, "error": str(e)})

        return health_status


class DocumentRouter:
    """Routes documents to appropriate parsers with fallback support."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize document router.

        Args:
            settings: Optional settings instance
        """
        self.settings = settings or Settings()
        self.format_detector = FormatDetector()
        self.parser_registry = ParserRegistry()
        self._deduplication_cache: set[str] = set()

        # Initialize PDF analyzer for pre-flight analysis (Phase 1c)
        self.pdf_analyzer = PDFDocumentAnalyzer(settings=self.settings)

    def create_document(
        self,
        source_path: str | Path | None = None,
        source_url: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Document:
        """Create a document from source path or URL.

        # #CRITICAL: External Resources: Must validate source accessibility
        # #VERIFY: Handle file not found, network errors gracefully

        Args:
            source_path: Path to source file
            source_url: URL to source content
            metadata: Optional metadata dictionary

        Returns:
            Document instance

        Raises:
            ValueError: If neither path nor URL provided
            UnsupportedFormatError: If format cannot be detected
        """
        if not source_path and not source_url:
            msg = "Either source_path or source_url must be provided"
            raise ValueError(msg)

        # Detect format
        if source_path:
            document_format = self.format_detector.detect_from_path(source_path)
            source_path_str = str(Path(source_path).resolve())
        else:
            document_format = self.format_detector.detect_from_url(source_url)  # type: ignore[arg-type]
            source_path_str = None

        if document_format == DocumentFormat.UNKNOWN:
            raise UnsupportedFormatError(
                format_detected="unknown",
                file_extension=Path(source_path).suffix if source_path else None,
            )

        # Create document
        return Document(
            source_path=source_path_str,
            source_url=source_url,
            format=document_format,
            metadata=metadata or {},
        )

    def is_duplicate(self, document: Document) -> bool:
        """Check if document has been processed before.

        # #ASSUME: Data Integrity: Hash-based deduplication is sufficient
        # #VERIFY: May need content-based similarity for near-duplicates

        Args:
            document: Document to check

        Returns:
            True if document is duplicate, False otherwise
        """
        if not document.source_path:
            return False

        # Calculate file hash
        path = Path(document.source_path)
        if not path.exists():
            return False

        try:
            with path.open("rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()

            if file_hash in self._deduplication_cache:
                return True

            self._deduplication_cache.add(file_hash)
            return False
        except Exception as e:
            logger.warning(f"Error checking for duplicate: {e}")
            return False

    def route_document(self, document: Document) -> ParserResult:
        """Route document to appropriate parser and process it.

        # #CRITICAL: Parser Failures: Must implement fallback chain for reliability
        # #VERIFY: Try all available parsers before failing

        # Phase 1c: Perform PDF pre-flight analysis and upscaling if needed

        Args:
            document: Document to process

        Returns:
            ParserResult from successful parser

        Raises:
            UnsupportedFormatError: If no parsers available for format
            ParserError: If all parsers fail
        """
        # Phase 1c: Perform pre-flight analysis for PDFs
        preflight_result: PDFPreflightResult | None = None
        original_source_path = document.source_path

        if document.format == DocumentFormat.PDF and document.source_path:
            try:
                logger.info("Performing PDF pre-flight analysis (Phase 1c)")
                preflight_result = self.pdf_analyzer.analyze(document.source_path)

                # Use upscaled version if available and successful
                if preflight_result.should_use_upscaled and preflight_result.upscaled_path:
                    logger.info(
                        f"Using upscaled PDF: {preflight_result.upscaled_path} "
                        f"(upscaling took {preflight_result.upscaling_result.get('processing_time', 0):.2f}s)",
                    )
                    document.source_path = preflight_result.upscaled_path

                    # Add upscaling metadata
                    document.metadata["upscaling"] = {
                        "performed": True,
                        "original_path": original_source_path,
                        "upscaled_path": preflight_result.upscaled_path,
                        "resolution_analysis": preflight_result.resolution_analysis,
                        "upscaling_result": preflight_result.upscaling_result,
                    }
                else:
                    document.metadata["upscaling"] = {
                        "performed": False,
                        "resolution_analysis": preflight_result.resolution_analysis,
                        "reason": "Resolution acceptable or upscaling failed",
                    }

            except Exception as e:
                logger.warning(f"PDF pre-flight analysis failed: {e}, proceeding with original PDF")
                document.metadata["upscaling"] = {
                    "performed": False,
                    "error": str(e),
                }

        # Get parsers for this format
        parsers = self.parser_registry.get_parsers(document.format)

        if not parsers:
            raise UnsupportedFormatError(
                format_detected=document.format.value,
                file_extension=Path(document.source_path).suffix if document.source_path else None,
            )

        # Try parsers in priority order
        errors: list[str] = []
        for parser in parsers:
            try:
                logger.info(f"Attempting to parse with {parser.name}")

                # Validate document
                if not parser.validate_document(document):
                    logger.warning(f"Document validation failed for {parser.name}")
                    continue

                # Parse document
                result = parser.parse(document)

                if result.success:
                    logger.info(f"Successfully parsed with {parser.name}")
                    document.update_status(ProcessingStatus.COMPLETED)
                    document.parser_used = parser.name
                    document.processing_time = result.processing_time
                    document.elements = result.elements
                    document.metadata.update(result.metadata)

                    # Cleanup temporary upscaled file if it exists
                    if preflight_result and preflight_result.upscaled_path:
                        try:
                            Path(preflight_result.upscaled_path).unlink(missing_ok=True)
                            logger.debug(f"Cleaned up temporary upscaled file: {preflight_result.upscaled_path}")
                        except Exception as cleanup_error:
                            logger.warning(f"Failed to cleanup upscaled file: {cleanup_error}")

                    return result

                errors.append(f"{parser.name}: {result.error_message}")

            except Exception as e:
                error_msg = f"{parser.name}: {e!s}"
                errors.append(error_msg)
                logger.warning(f"Parser {parser.name} failed: {e}")

        # All parsers failed
        document.update_status(ProcessingStatus.FAILED)

        # Cleanup temporary upscaled file if parsing failed
        if preflight_result and preflight_result.upscaled_path:
            with contextlib.suppress(Exception):
                Path(preflight_result.upscaled_path).unlink(missing_ok=True)

        raise ParserError(
            message=f"All parsers failed for document format {document.format.value}",
            parser_name="all",
            document_path=document.source_path,
            details={"errors": errors},
        )

    def process_document(
        self,
        source_path: str | Path | None = None,
        source_url: str | None = None,
        metadata: dict[str, Any] | None = None,
        skip_duplicate_check: bool = False,
    ) -> tuple[Document, ParserResult]:
        """Process a document end-to-end.

        Args:
            source_path: Path to source file
            source_url: URL to source content
            metadata: Optional metadata dictionary
            skip_duplicate_check: Skip deduplication check

        Returns:
            Tuple of (Document, ParserResult)

        Raises:
            ValueError: If neither path nor URL provided
            UnsupportedFormatError: If format not supported
            ParserError: If processing fails
        """
        # Create document
        document = self.create_document(source_path=source_path, source_url=source_url, metadata=metadata)

        # Check for duplicates
        if not skip_duplicate_check and self.is_duplicate(document):
            logger.info(f"Duplicate document detected: {document.source_path}")
            document.update_status(ProcessingStatus.COMPLETED)
            # Return empty result for duplicate
            return document, ParserResult(
                success=True,
                parser_name="cache",
                processing_time=0.0,
                metadata={"cached": True, "duplicate": True},
            )

        # Route and process
        document.update_status(ProcessingStatus.PROCESSING)
        result = self.route_document(document)

        return document, result
