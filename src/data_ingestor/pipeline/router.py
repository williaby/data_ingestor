"""Document router for selecting appropriate parsers.

This module implements the top-level **pipeline orchestrator** for the
data-ingestor RAG pipeline. The orchestrator is responsible for:

1. Creating a :class:`~data_ingestor.core.models.Document` from a source
   path or URL (format detection happens here).
2. Performing a SHA-256-based deduplication check against an in-memory
   cache so the same source file is not processed twice within a single
   process lifetime.
3. Running an optional PDF pre-flight stage (resolution analysis and
   upscaling).
4. Dispatching the document to the highest-priority parser registered
   for its format, with automatic fallback to lower-priority parsers if
   higher-priority ones fail.

The orchestrator does not write to any external storage and does not
call any LLM or cloud APIs directly; downstream chunking and export
stages are invoked by callers (typically the CLI in
:mod:`data_ingestor.cli.main`).

Pipeline sequence (per call to
:meth:`DocumentRouter.process_document`)::

    create_document  ->  is_duplicate  ->  route_document
                                              |
                                              v
                                      PDF pre-flight (PDFs only)
                                              |
                                              v
                                      Parser fallback chain
                                              |
                                              v
                                      ParserResult returned

Idempotency: A second call with the same ``source_path`` within the
same router instance returns a cached :class:`ParserResult` with
``metadata={"cached": True, "duplicate": True}`` and does **not**
invoke any parser. The cache is in-memory only; restarting the process
clears it. Callers needing durable idempotency should layer their own
content-addressed storage on top.
"""

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
        doc = Document(
            source_path=source_path_str,
            source_url=source_url,
            format=document_format,
            metadata=metadata or {},
        )

        return doc

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
        """Route a document through the parser fallback chain.

        For PDFs this also runs a **pre-flight stage** that analyzes
        page-image resolution and may upscale the PDF to improve OCR
        quality (see
        :class:`~data_ingestor.pipeline.pdf_analyzer.PDFDocumentAnalyzer`).
        The upscaled artifact is a temporary file that is removed
        before this method returns.

        Parsers are tried in priority order (lower
        :meth:`BaseParser.get_priority` wins). For each parser the
        document is first validated via
        :meth:`BaseParser.validate_document`; only if validation passes
        is :meth:`BaseParser.parse` invoked. A parser that returns a
        :class:`ParserResult` with ``success=False`` or that raises an
        exception is recorded in ``errors`` and the next parser in the
        chain is tried.

        **Side effects:**

        * On success: mutates ``document.status``,
          ``document.parser_used``, ``document.processing_time``,
          ``document.elements``, and merges parser metadata into
          ``document.metadata``.
        * On failure: sets ``document.status`` to
          :attr:`ProcessingStatus.FAILED`.
        * For PDFs: may write and then delete a temporary upscaled file
          beneath the system temp directory.

        Args:
            document: A :class:`Document` whose ``format`` and
                ``source_path`` are already populated. The document is
                mutated in place.

        Returns:
            The :class:`ParserResult` produced by the first parser that
            reports ``success=True``.

        Raises:
            UnsupportedFormatError: No parser is registered for
                ``document.format``. Raised *before* any parser is
                invoked.
            ParserError: Every registered parser failed. The
                exception's ``details["errors"]`` lists the per-parser
                error message; ``parser_name`` is ``"all"`` to
                indicate exhaustion of the fallback chain. The
                exception is *propagated*, not swallowed, so upstream
                stages cannot silently continue.
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
                        f"(upscaling took {preflight_result.upscaling_result.get('processing_time', 0):.2f}s)"
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
            try:
                Path(preflight_result.upscaled_path).unlink(missing_ok=True)
            except Exception:
                pass

        error_summary = "; ".join(errors)
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
        """Run the full ingestion pipeline for a single document.

        This is the **public orchestrator entry point**. It is triggered
        by the CLI (``data-ingestor process``), the future REST API,
        and any programmatic caller. The orchestrator runs the
        following stages in order:

        1. **Create document** -- detect the format and build a
           :class:`Document` model (calls
           :meth:`create_document`).
        2. **Deduplicate** -- unless ``skip_duplicate_check`` is True,
           hash the file contents (SHA-256) and short-circuit if the
           hash has already been seen by this router instance.
        3. **Route + parse** -- dispatch to the parser fallback chain
           via :meth:`route_document`. For PDFs this also runs the
           pre-flight upscaling stage.

        **Input schema:** At least one of ``source_path`` or
        ``source_url`` MUST be provided. If both are supplied the
        method accepts them and ``source_path`` takes precedence for
        format detection and on-disk lookup; ``source_url`` is still
        recorded on the resulting :class:`Document` for downstream
        stages but is not fetched here. ``source_path`` must exist on
        the local filesystem (validated by :class:`Document`'s field
        validator); ``source_url`` is treated as opaque.

        **Output schema (success or duplicate paths only):** Returns
        ``(Document, ParserResult)``. The :class:`Document` has its
        ``status`` set to :attr:`ProcessingStatus.COMPLETED` and its
        ``elements`` field is populated. The :class:`ParserResult`
        carries the raw extraction result (success flag, elements,
        metadata, timing). For duplicates the returned
        :class:`ParserResult` has ``parser_name="cache"`` and
        ``metadata={"cached": True, "duplicate": True}``. Failure
        paths do **not** return -- they raise (see Raises below); the
        internal :class:`Document` is mutated to
        :attr:`ProcessingStatus.FAILED` for the all-parsers-failed
        case but is not handed back to the caller.

        **Side effects:**

        * Mutates the router's in-memory deduplication cache.
        * For PDFs, may write a temporary upscaled PDF under the system
          temp directory; this file is unlinked before this method
          returns regardless of success or failure.
        * Mutates the :class:`Document` passed through internally
          (status, ``parser_used``, ``processing_time``, ``elements``,
          ``metadata``).

        **Idempotency:** Two calls with the same ``source_path`` within
        the lifetime of one ``DocumentRouter`` instance are idempotent
        at the dedup layer (second call returns the cached short-circuit
        result without re-parsing). The cache is process-local and does
        not persist across restarts; pass
        ``skip_duplicate_check=True`` to force re-processing.

        Args:
            source_path: Path to a local source file. May be combined
                with ``source_url``; when both are present
                ``source_path`` is the canonical input.
            source_url: URL identifying the source. URL-based fetching
                is not implemented in this stage; the URL is recorded
                on the document for downstream stages.
            metadata: Optional initial metadata merged into
                ``Document.metadata``.
            skip_duplicate_check: When True, bypass the SHA-256 dedup
                cache and always run the full parse chain.

        Returns:
            Tuple of (``Document``, ``ParserResult``). Both reflect the
            outcome of the pipeline; on duplicate hits the result is
            synthesized and no parser is invoked.

        Raises:
            ValueError: Neither ``source_path`` nor ``source_url`` was
                provided, or ``source_path`` does not exist.
            UnsupportedFormatError: Format detection returned
                :attr:`DocumentFormat.UNKNOWN` or no parser is
                registered for the detected format. The pipeline does
                **not** silently downgrade -- it raises so callers can
                surface the problem.
            ParserError: Every parser in the fallback chain failed.
                ``details["errors"]`` contains the per-parser error
                messages so callers can diagnose the failure mode.
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
