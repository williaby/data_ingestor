"""PDF parser implementations."""

import logging
import time
from pathlib import Path
from typing import Any, cast

import fitz  # PyMuPDF  # type: ignore[import-untyped]

from data_ingestor.core.base import BaseParser
from data_ingestor.core.exceptions import ParserError
from data_ingestor.core.models import Document, DocumentElement, DocumentFormat, ElementMetadata, ElementType, ParserResult

logger = logging.getLogger(__name__)


class PyMuPDFParser(BaseParser):
    """PDF parser using PyMuPDF library.

    Args:
        config (dict[str, Any] | None): Optional configuration dictionary.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.name = "PyMuPDFParser"

    def supports_format(self, document_format: DocumentFormat) -> bool:
        """Check if this parser supports PDF format.

        Args:
            document_format (DocumentFormat): Format to check.

        Returns:
            bool: True if PDF, False otherwise.
        """
        return document_format == DocumentFormat.PDF

    def parse(self, document: Document) -> ParserResult:
        """Parse PDF document and extract text and structure.

        # #CRITICAL: Memory Management: Large PDFs can exhaust memory
        # #VERIFY: Process page-by-page to limit memory usage

        Args:
            document (Document): Document to parse.

        Returns:
            ParserResult: Parser result with extracted elements.

        Raises:
            ParserError: If parsing fails.
        """
        if not document.source_path:
            raise ParserError(
                message="Source path required for PDF parsing",
                parser_name=self.name,
            )

        start_time = time.time()
        elements: list[DocumentElement] = []
        warnings: list[str] = []

        try:
            # Open PDF document
            # #CRITICAL: External Resources: File may be corrupted or password-protected
            # #VERIFY: Handle encryption and corruption gracefully
            pdf_doc = fitz.open(document.source_path)

            # Extract metadata
            metadata = self._extract_metadata(pdf_doc)

            # Process each page
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]

                # Extract text blocks with position information
                blocks = page.get_text("dict")["blocks"]

                for block in blocks:
                    if block["type"] == 0:  # Text block
                        for line in block.get("lines", []):
                            text_content = ""
                            for span in line.get("spans", []):
                                text_content += span.get("text", "")

                            if text_content.strip():
                                # Determine element type based on font size
                                # #ASSUME: Format Detection: Font size heuristic may misclassify headers
                                # #VERIFY: Should use more sophisticated layout analysis
                                font_size = span.get("size", 12) if line.get("spans") else 12
                                element_type = self._classify_text_block(text_content, font_size)

                                element = DocumentElement(
                                    element_type=element_type,
                                    content=text_content.strip(),
                                    page_number=page_num + 1,
                                    bbox=(
                                        block["bbox"][0],
                                        block["bbox"][1],
                                        block["bbox"][2],
                                        block["bbox"][3],
                                    ),
                                    metadata=ElementMetadata(extra={"font_size": font_size}),
                                )
                                elements.append(element)

                # Extract images
                image_list = page.get_images()
                if image_list:
                    warnings.append(f"Page {page_num + 1} contains {len(image_list)} images (not extracted)")

            pdf_doc.close()

            processing_time = time.time() - start_time

            return ParserResult(
                success=True,
                elements=elements,
                metadata=metadata,
                parser_name=self.name,
                processing_time=processing_time,
                warnings=warnings,
            )

        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Failed to parse PDF: {e!s}"
            logger.error(error_msg)

            return ParserResult(
                success=False,
                parser_name=self.name,
                processing_time=processing_time,
                error_message=error_msg,
            )

    def _extract_metadata(self, pdf_doc: fitz.Document) -> dict[str, Any]:
        """Extract metadata from PDF document.

        Args:
            pdf_doc (fitz.Document): PyMuPDF document object.

        Returns:
            dict[str, Any]: Dictionary with metadata.
        """
        metadata = pdf_doc.metadata or {}

        return {
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "subject": metadata.get("subject", ""),
            "keywords": metadata.get("keywords", ""),
            "creator": metadata.get("creator", ""),
            "producer": metadata.get("producer", ""),
            "creation_date": metadata.get("creationDate", ""),
            "modification_date": metadata.get("modDate", ""),
            "page_count": len(pdf_doc),
        }

    def _classify_text_block(self, text: str, font_size: float) -> ElementType:
        """Classify text block based on content and formatting.

        # #ASSUME: Format Detection: Simple heuristics may misclassify elements
        # #VERIFY: Use more sophisticated NLP-based classification

        Args:
            text (str): Text content.
            font_size (float): Font size in points.

        Returns:
            ElementType: Classified element type.
        """
        # Large font = likely heading or title
        if font_size > 16:
            return ElementType.TITLE
        if font_size > 14:
            return ElementType.HEADING

        # All caps and short = likely heading
        if text.isupper() and len(text) < 100:
            return ElementType.HEADING

        # Default to paragraph
        return ElementType.PARAGRAPH

    def health_check(self) -> bool:
        """Check if PyMuPDF is working correctly.

        Returns:
            bool: True if operational.
        """
        try:
            # Try to access PyMuPDF version
            _ = fitz.version
            return True
        except Exception as e:
            logger.error(f"PyMuPDF health check failed: {e}")
            return False


class PyMuPDF4LLMParser(BaseParser):
    """PDF parser using PyMuPDF4LLM for LLM-optimized extraction.

    Args:
        config (dict[str, Any] | None): Optional configuration dictionary.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.name = "PyMuPDF4LLMParser"

    def supports_format(self, document_format: DocumentFormat) -> bool:
        """Check if this parser supports PDF format.

        Args:
            document_format (DocumentFormat): Format to check.

        Returns:
            bool: True if PDF, False otherwise.
        """
        return document_format == DocumentFormat.PDF

    def parse(self, document: Document) -> ParserResult:
        """Parse PDF using PyMuPDF4LLM for better structure preservation.

        # #CRITICAL: Library Dependency: pymupdf4llm may not be installed
        # #VERIFY: Gracefully degrade if library unavailable

        Args:
            document (Document): Document to parse.

        Returns:
            ParserResult: Parser result with extracted elements.

        Raises:
            ParserError: If parsing fails.
        """
        if not document.source_path:
            raise ParserError(
                message="Source path required for PDF parsing",
                parser_name=self.name,
            )

        start_time = time.time()

        try:
            import pymupdf4llm  # type: ignore[import-untyped]

            # Extract markdown from PDF
            md_text = pymupdf4llm.to_markdown(document.source_path)

            # Convert markdown to elements
            # #ASSUME: Format Conversion: Markdown parsing accurately preserves structure
            # #VERIFY: Validate structure preservation with test documents
            elements = self._markdown_to_elements(md_text)

            # Extract basic metadata
            metadata = {"page_count": None}  # pymupdf4llm doesn't provide page count easily

            processing_time = time.time() - start_time

            return ParserResult(
                success=True,
                elements=elements,
                raw_content=md_text,
                metadata=metadata,
                parser_name=self.name,
                processing_time=processing_time,
            )

        except ImportError:
            # Library not available
            error_msg = "pymupdf4llm not installed"
            logger.warning(error_msg)
            return ParserResult(
                success=False,
                parser_name=self.name,
                processing_time=time.time() - start_time,
                error_message=error_msg,
            )

        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Failed to parse PDF with PyMuPDF4LLM: {e!s}"
            logger.error(error_msg)

            return ParserResult(
                success=False,
                parser_name=self.name,
                processing_time=processing_time,
                error_message=error_msg,
            )

    def _markdown_to_elements(self, markdown: str) -> list[DocumentElement]:
        """Convert markdown text to document elements.

        Args:
            markdown (str): Markdown text.

        Returns:
            list[DocumentElement]: List of document elements.
        """
        elements: list[DocumentElement] = []
        lines = markdown.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect headings
            if line.startswith("# "):
                element_type = ElementType.TITLE
                content = line[2:].strip()
            elif line.startswith("## ") or line.startswith("### "):
                element_type = ElementType.HEADING
                content = line.lstrip("#").strip()
            else:
                element_type = ElementType.PARAGRAPH
                content = line

            element = DocumentElement(element_type=element_type, content=content)
            elements.append(element)

        return elements

    def health_check(self) -> bool:
        """Check if PyMuPDF4LLM is available.

        Returns:
            bool: True if operational.
        """
        try:
            import pymupdf4llm

            _ = pymupdf4llm.__version__
            return True
        except ImportError:
            logger.warning("pymupdf4llm not available")
            return False
        except Exception as e:
            logger.error(f"PyMuPDF4LLM health check failed: {e}")
            return False


class MarkerParser(BaseParser):
    """PDF parser using Marker for advanced extraction with tables and formulas.

    Marker provides high-quality PDF-to-Markdown conversion with:
    - Accurate table structure preservation
    - Formula extraction (LaTeX format)
    - Multi-column layout handling
    - Image extraction and positioning
    - Better handling of complex PDFs

    Args:
        config (dict[str, Any] | None): Optional configuration dictionary.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        # #CRITICAL: GPU Availability: Marker performs best with GPU
        # #VERIFY: Must detect GPU and configure appropriately
        super().__init__(config)
        self.name = "MarkerParser"
        self._marker_available = False
        self._gpu_available = False

        # LLM configuration with fallback support
        # #CRITICAL: Model Fallback: Primary (free) model may have rate limits or availability issues
        # #VERIFY: Fallback to paid model ensures reliability
        import os

        self.use_llm = os.getenv("MARKER_USE_LLM", "false").lower() == "true"
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

        # Primary model (free tier - Llama 4 Maverick)
        self.llm_model_primary = os.getenv("MARKER_LLM_MODEL", "meta-llama/llama-4-maverick:free")

        # Fallback model (paid tier - Gemini 2.5 Flash Lite)
        self.llm_model_fallback = os.getenv("MARKER_LLM_FALLBACK_MODEL", "google/gemini-2.5-flash-lite")

        # Enable/disable fallback
        self.enable_fallback = os.getenv("MARKER_ENABLE_FALLBACK", "true").lower() == "true"

        # Rate limiting configuration
        # #CRITICAL: Rate Limit Compliance: OpenRouter enforces 20 RPM for :free models
        # #VERIFY: Must rate limit to avoid 429 errors and API blocks
        from data_ingestor.core.config import Settings
        from data_ingestor.utils.rate_limiter import OpenRouterRateLimiter

        settings = Settings()
        self.enable_rate_limiting = settings.openrouter_enable_rate_limiting
        self.rate_limit_timeout = settings.openrouter_rate_limit_timeout
        self.openrouter_tier = settings.openrouter_tier

        # Initialize rate limiter if enabled
        self.rate_limiter: OpenRouterRateLimiter | None = None
        if self.enable_rate_limiting and self.use_llm:
            self.rate_limiter = OpenRouterRateLimiter(tier=self.openrouter_tier)  # type: ignore[arg-type]
            logger.info(f"OpenRouter rate limiting enabled ({self.openrouter_tier} tier)")

        if self.use_llm:
            if not self.openrouter_api_key:
                logger.warning("MARKER_USE_LLM enabled but OPENROUTER_API_KEY not found. Disabling LLM.")
                self.use_llm = False
            else:
                logger.info(f"Marker LLM enabled with primary model: {self.llm_model_primary}")
                if self.enable_fallback:
                    logger.info(f"Fallback model configured: {self.llm_model_fallback}")

        # Check availability
        try:
            import marker  # noqa: F401  # type: ignore[import-untyped]

            self._marker_available = True

            # Check GPU availability
            # #CRITICAL: GPU Detection: Must handle various CUDA configurations
            # #VERIFY: Test on CPU-only systems for graceful degradation
            try:
                import torch

                self._gpu_available = torch.cuda.is_available()
                if self._gpu_available:
                    logger.info(f"Marker: GPU available (CUDA {torch.version.cuda})")
                else:
                    logger.info("Marker: Running in CPU mode")
            except ImportError:
                logger.warning("torch not available, Marker will use CPU")

        except ImportError:
            logger.warning("marker-pdf not installed. Install with: poetry install --with advanced-pdf")

    def supports_format(self, document_format: DocumentFormat) -> bool:
        """Check if this parser supports PDF format.

        Args:
            document_format (DocumentFormat): Format to check.

        Returns:
            bool: True if PDF and Marker is available, False otherwise.
        """
        return document_format == DocumentFormat.PDF and self._marker_available

    def parse(self, document: Document) -> ParserResult:
        """Parse PDF using Marker for high-quality extraction.

        # #CRITICAL: Memory Management: Marker loads models which consume significant memory
        # #VERIFY: Monitor memory usage and implement resource limits

        # #CRITICAL: Processing Time: Marker is slower than simple parsers
        # #VERIFY: Consider async processing or timeout limits

        Args:
            document (Document): Document to parse.

        Returns:
            ParserResult: Parser result with extracted elements.

        Raises:
            ParserError: If parsing fails.
            Exception: For unexpected errors during parsing.
        """
        if not document.source_path:
            raise ParserError(
                message="Source path required for PDF parsing",
                parser_name=self.name,
            )

        if not self._marker_available:
            return ParserResult(
                success=False,
                parser_name=self.name,
                processing_time=0.0,
                error_message="marker-pdf not installed",
            )

        start_time = time.time()

        try:
            # Marker 1.10.x API - completely different from 0.2.x
            from marker.config.parser import ConfigParser
            from marker.converters.pdf import PdfConverter
            from marker.models import create_model_dict

            # Load Marker models
            # #CRITICAL: Model Loading: First-time model download can take minutes (~2GB)
            # #VERIFY: Implement model caching and pre-loading strategy
            logger.info("Loading Marker models...")

            # Create model dict with GPU if available
            device = "cuda" if self._gpu_available else "cpu"
            dtype_str = "float16" if self._gpu_available else "float32"

            model_dict = create_model_dict(device=device, dtype=dtype_str)

            # Create converter with default config
            # #ASSUME: Marker Configuration: Default configuration suitable for most PDFs
            # #VERIFY: May need custom config for specific document types
            logger.info(f"Processing {Path(document.source_path).name} with Marker...")

            config = {}
            if self.config.get("max_pages"):
                config["max_pages"] = self.config.get("max_pages")

            # Quality and accuracy improvements
            # #ASSUME: Quality Settings: These settings improve accuracy without issues
            # #VERIFY: Monitor processing time and quality improvements
            config["paginate_output"] = True  # Add page separators for page tracking
            config["force_ocr"] = False  # Disabled: Too slow for real-world PDFs (was causing 20+ min hangs)
            config["debug"] = True  # Enable debug logging for diagnostics

            # Configure LLM enhancement with fallback support
            # #CRITICAL: LLM API Configuration: API key must be valid
            # #VERIFY: Test with actual OpenRouter API key
            output = None
            llm_model_used = None

            if self.use_llm and self.openrouter_api_key:
                # Try primary model first
                try:
                    logger.info(f"Attempting LLM enhancement with primary model: {self.llm_model_primary}")
                    output = self._process_with_llm(
                        document.source_path, model_dict, config.copy(), self.llm_model_primary,
                    )
                    llm_model_used = self.llm_model_primary
                    logger.info(f"✓ Successfully processed with primary model: {self.llm_model_primary}")

                except Exception as e:
                    # Check if it's an API-related error that warrants fallback
                    # #CRITICAL: Error Classification: Distinguish OpenRouter vs downstream provider errors
                    # #VERIFY: Different error codes have different retry/fallback strategies
                    error_str = str(e).lower()

                    # Categorize error types
                    is_rate_limit_error = any(
                        keyword in error_str
                        for keyword in ["rate limit", "429", "too many requests"]
                    )

                    is_auth_error = any(
                        keyword in error_str
                        for keyword in ["auth", "authentication", "401", "403", "unauthorized", "forbidden"]
                    )

                    is_downstream_provider_error = any(
                        keyword in error_str
                        for keyword in ["400", "bad request", "invalid request", "model not found", "model unavailable"]
                    )

                    is_server_error = any(
                        keyword in error_str
                        for keyword in ["500", "502", "503", "504", "internal server error", "gateway"]
                    )

                    is_connection_error = any(
                        keyword in error_str
                        for keyword in ["connection", "timeout", "network", "unreachable"]
                    )

                    # Log detailed error classification
                    if is_rate_limit_error:
                        logger.warning(f"Rate limit error detected (429): {e}")
                    elif is_auth_error:
                        logger.error(f"Authentication error (401/403): Check OPENROUTER_API_KEY. Error: {e}")
                    elif is_downstream_provider_error:
                        logger.warning(
                            f"Downstream provider error (400/model unavailable): "
                            f"Likely from OpenAI/model provider, not OpenRouter. Error: {e}"
                        )
                    elif is_server_error:
                        logger.warning(f"Server error (5xx): Temporary issue. Error: {e}")
                    elif is_connection_error:
                        logger.warning(f"Connection error: Network issue. Error: {e}")

                    # Determine if we should fallback
                    is_api_error = (
                        is_rate_limit_error
                        or is_auth_error
                        or is_downstream_provider_error
                        or is_server_error
                        or is_connection_error
                    )

                    if is_api_error and self.enable_fallback:
                        logger.warning(f"Primary model ({self.llm_model_primary}) failed with API error: {e}")
                        logger.info(f"Attempting fallback to: {self.llm_model_fallback}")

                        try:
                            output = self._process_with_llm(
                                document.source_path, model_dict, config.copy(), self.llm_model_fallback,
                            )
                            llm_model_used = self.llm_model_fallback
                            logger.info(f"✓ Successfully processed with fallback model: {self.llm_model_fallback}")

                        except Exception as fallback_error:
                            logger.error(f"Fallback model also failed: {fallback_error}")
                            logger.info("Processing without LLM enhancement")
                            # Process without LLM as last resort
                            output = self._process_without_llm(document.source_path, model_dict, config.copy())
                    else:
                        # Non-API error or fallback disabled, re-raise
                        logger.error(f"LLM processing failed: {e}")
                        if self.enable_fallback:
                            logger.info("Error not API-related, processing without LLM")
                            output = self._process_without_llm(document.source_path, model_dict, config.copy())
                        else:
                            raise

            if output is None:
                # No LLM configured, process normally
                output = self._process_without_llm(document.source_path, model_dict, config.copy())

            # Extract markdown string and metadata from MarkdownOutput
            full_text = output.markdown
            images = output.images
            metadata = output.metadata

            # Convert markdown to elements
            elements = self._markdown_to_elements(full_text)

            # Fix 4: Enhance element metadata (confidence, parent_id, category_depth)
            elements = self._enhance_element_metadata(elements, metadata)

            # Enhance metadata
            # Fix 1: Calculate page_count from elements if Marker doesn't provide it
            page_count = metadata.get("pages", 0)
            if page_count == 0 and elements:
                # Calculate from max page number in elements
                page_numbers = [el.metadata.page_number for el in elements if el.metadata.page_number is not None]
                page_count = max(page_numbers) if page_numbers else 0

            # Fix 2: Extract TOC from headings if Marker doesn't provide it
            toc = metadata.get("toc", [])
            if not toc:
                toc = self._extract_toc_from_elements(elements)

            # Fix 3: Detect languages if Marker doesn't provide them
            languages = metadata.get("languages", [])
            if not languages and elements:
                languages = self._detect_languages(elements)

            enhanced_metadata = {
                "page_count": page_count,
                "toc": toc,
                "languages": languages,
                "images_extracted": len(images),
                "marker_version": metadata.get("version", "unknown"),
                "gpu_used": self._gpu_available,
                "llm_enhanced": self.use_llm and llm_model_used is not None,
                "llm_model": llm_model_used,
                "llm_fallback_used": llm_model_used == self.llm_model_fallback if llm_model_used else False,
            }

            processing_time = time.time() - start_time
            logger.info(f"Marker processing completed in {processing_time:.2f}s")

            return ParserResult(
                success=True,
                elements=elements,
                raw_content=full_text,
                metadata=enhanced_metadata,
                parser_name=self.name,
                processing_time=processing_time,
            )

        except ImportError as e:
            error_msg = f"Marker dependencies not available: {e}"
            logger.error(error_msg)
            return ParserResult(
                success=False,
                parser_name=self.name,
                processing_time=time.time() - start_time,
                error_message=error_msg,
            )

        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Failed to parse PDF with Marker: {e!s}"
            logger.error(error_msg)

            return ParserResult(
                success=False,
                parser_name=self.name,
                processing_time=processing_time,
                error_message=error_msg,
            )

    def _process_with_llm(self, source_path: str, model_dict: dict, config: dict, llm_model: str) -> Any:
        """Process PDF with LLM enhancement using specified model.

        # #CRITICAL: Rate Limiting: Must acquire rate limit permission before API call
        # #VERIFY: Implement exponential backoff on 429 errors

        Args:
            source_path (str): Path to PDF file.
            model_dict (dict): Marker model dictionary.
            config (dict): Configuration dictionary.
            llm_model (str): LLM model to use.

        Returns:
            Any: MarkdownOutput object from Marker.

        Raises:
            ValueError: If rate limit timeout exceeded.
            RuntimeError: If retry logic reaches unexpected code path.
            Exception: If processing fails or rate limit exceeded.
        """
        from marker.config.parser import ConfigParser
        from marker.converters.pdf import PdfConverter

        # Acquire rate limit permission if enabled
        if self.rate_limiter is not None:
            logger.info(f"Acquiring rate limit permission for {llm_model}...")
            try:
                acquired = self.rate_limiter.acquire(
                    model=llm_model,
                    timeout=self.rate_limit_timeout,
                )
                if not acquired:
                    raise ValueError(
                        f"Rate limit timeout ({self.rate_limit_timeout}s) exceeded. "
                        "Too many concurrent requests or daily limit reached."
                    )
                logger.info("✓ Rate limit permission acquired")

                # Log rate limiter stats
                stats = self.rate_limiter.get_stats()
                logger.debug(f"Rate limiter stats: {stats}")

            except ValueError as e:
                # Daily limit exceeded or timeout
                logger.error(f"Rate limit error: {e}")
                raise

        logger.info(f"Configuring LLM enhancement with model: {llm_model}")
        config["use_llm"] = True
        config["llm_service"] = "marker.services.openai.OpenAIService"
        config["openai_api_key"] = self.openrouter_api_key
        config["openai_base_url"] = "https://openrouter.ai/api/v1"
        config["openai_model"] = llm_model
        config["redo_inline_math"] = True  # Highest quality inline math with LLM

        # Create ConfigParser and converter
        config_parser = ConfigParser(config)
        converter = PdfConverter(
            artifact_dict=model_dict,
            config=config_parser.generate_config_dict(),
            llm_service=config_parser.get_llm_service(),
        )

        # Convert PDF (with exponential backoff on rate limit errors)
        max_retries = 3
        base_delay = 1.0

        for attempt in range(max_retries):
            try:
                return converter(source_path)

            except Exception as e:
                error_str = str(e).lower()

                # Check if it's a rate limit error (429)
                if "429" in error_str or "rate limit" in error_str or "too many requests" in error_str:
                    if attempt < max_retries - 1:
                        # Exponential backoff: 1s, 2s, 4s
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            f"Rate limit error (429) on attempt {attempt + 1}/{max_retries}. "
                            f"Retrying in {delay}s..."
                        )
                        time.sleep(delay)
                        continue
                    else:
                        logger.error("Rate limit error persists after retries")
                        raise

                # Non-rate-limit error, re-raise immediately
                raise

        # Should not reach here
        raise RuntimeError("Unexpected code path in rate limiting retry logic")

    def _process_without_llm(self, source_path: str, model_dict: dict, config: dict) -> Any:
        """Process PDF without LLM enhancement.

        Args:
            source_path (str): Path to PDF file.
            model_dict (dict): Marker model dictionary.
            config (dict): Configuration dictionary.

        Returns:
            Any: MarkdownOutput object from Marker.
        """
        from marker.config.parser import ConfigParser
        from marker.converters.pdf import PdfConverter

        logger.info("Processing without LLM enhancement")
        config["use_llm"] = False

        # Create ConfigParser and converter
        config_parser = ConfigParser(config)
        converter = PdfConverter(
            artifact_dict=model_dict,
            config=config_parser.generate_config_dict(),
            llm_service=None,
        )

        # Convert PDF
        return converter(source_path)

    def _markdown_to_elements(self, markdown: str) -> list[DocumentElement]:
        """Convert Marker's markdown output to document elements.

        # #ASSUME: Markdown Format: Marker's markdown format is consistent
        # #VERIFY: May need more sophisticated parsing for complex structures

        Args:
            markdown (str): Markdown text from Marker.

        Returns:
            list[DocumentElement]: List of document elements.
        """
        import re

        from data_ingestor.core.models import ElementMetadata

        elements: list[DocumentElement] = []
        lines = markdown.split("\n")

        in_table = False
        table_lines: list[str] = []
        current_page = 1  # Track current page number

        for line in lines:
            line_stripped = line.strip()

            # Detect page markers (format: "{N}" where N is 0-indexed page number)
            # #ASSUME: Page Markers: paginate_output uses {N} format (0-indexed)
            # #VERIFY: Format confirmed from Marker 1.10.x output
            page_match = re.match(r"^\{(\d+)\}", line_stripped)
            if page_match:
                # Convert from 0-indexed to 1-indexed
                current_page = int(page_match.group(1)) + 1
                logger.debug(f"Detected page marker: page {current_page}")
                continue

            # Also skip separator lines (dashes following page markers)
            if re.match(r"^-{10,}$", line_stripped):
                continue

            if not line_stripped:
                # Flush table if we were in one
                if in_table and table_lines:
                    table_content = "\n".join(table_lines)
                    metadata = ElementMetadata(page_number=current_page)
                    element = DocumentElement(element_type=ElementType.TABLE, content=table_content, metadata=metadata)
                    elements.append(element)
                    table_lines = []
                    in_table = False
                continue

            # Detect table (Markdown tables have | characters)
            if "|" in line_stripped:
                in_table = True
                table_lines.append(line_stripped)
                continue

            # If we were in a table, flush it
            if in_table and table_lines:
                table_content = "\n".join(table_lines)
                metadata = ElementMetadata(page_number=current_page)
                element = DocumentElement(element_type=ElementType.TABLE, content=table_content, metadata=metadata)
                elements.append(element)
                table_lines = []
                in_table = False

            # Detect formulas (LaTeX in $$...$$)
            if line_stripped.startswith("$$") and line_stripped.endswith("$$"):
                content = line_stripped[2:-2].strip()
                metadata = ElementMetadata(page_number=current_page)
                element = DocumentElement(element_type=ElementType.FORMULA, content=content, metadata=metadata)
                elements.append(element)
                continue

            # Detect headings
            if line_stripped.startswith("# "):
                element_type = ElementType.TITLE
                content = line_stripped[2:].strip()
            elif line_stripped.startswith("## ") or line_stripped.startswith("### "):
                element_type = ElementType.HEADING
                content = line_stripped.lstrip("#").strip()
            elif line_stripped.startswith("- ") or line_stripped.startswith("* "):
                element_type = ElementType.LIST
                content = line_stripped
            else:
                element_type = ElementType.PARAGRAPH
                content = line_stripped

            if content:
                metadata = ElementMetadata(page_number=current_page)
                element = DocumentElement(element_type=element_type, content=content, metadata=metadata)
                elements.append(element)

        # Flush any remaining table
        if in_table and table_lines:
            table_content = "\n".join(table_lines)
            metadata = ElementMetadata(page_number=current_page)
            element = DocumentElement(element_type=ElementType.TABLE, content=table_content, metadata=metadata)
            elements.append(element)

        return elements

    def health_check(self) -> bool:
        """Check if Marker is available and operational.

        Returns:
            bool: True if operational.
        """
        if not self._marker_available:
            return False

        try:
            # Try to import core marker modules
            from marker.convert import convert_single_pdf  # noqa: F401
            from marker.models import load_all_models  # noqa: F401

            return True
        except ImportError as e:
            logger.error(f"Marker health check failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Marker health check error: {e}")
            return False

    def _extract_toc_from_elements(self, elements: list[DocumentElement]) -> list[dict[str, Any]]:
        """Extract table of contents from document elements.

        # #ASSUME: Document Structure: Headings represent document hierarchy
        # #VERIFY: May need more sophisticated logic for complex documents

        Args:
            elements (list[DocumentElement]): List of document elements.

        Returns:
            list[dict[str, Any]]: Table of contents as list of dicts with title, level, and page.
        """
        toc: list[dict[str, Any]] = []

        for element in elements:
            # Include titles and headings in TOC
            if element.element_type in (ElementType.TITLE, ElementType.HEADING):
                # Determine level: Title = 1, Heading = 2 (can be refined)
                level = 1 if element.element_type == ElementType.TITLE else 2

                # Use category_depth if available for more precise levels
                if element.metadata.category_depth is not None:
                    level = element.metadata.category_depth

                toc_entry = {
                    "title": element.content[:100],  # Limit to 100 chars
                    "level": level,
                    "page": element.metadata.page_number or 0,
                    "element_id": element.metadata.element_id,
                }
                toc.append(toc_entry)

        logger.debug(f"Extracted {len(toc)} TOC entries from elements")
        return toc

    def _detect_languages(self, elements: list[DocumentElement]) -> list[str]:
        """Detect languages present in document elements.

        # #CRITICAL: Library Dependency: langdetect may not be installed
        # #VERIFY: Gracefully degrade if library unavailable

        Args:
            elements (list[DocumentElement]): List of document elements.

        Returns:
            list[str]: List of detected language codes (ISO 639-1).
        """
        try:
            from collections import Counter

            from langdetect import LangDetectException, detect

            # Sample text from elements (combine up to 1000 chars for better accuracy)
            sample_texts: list[str] = []
            total_chars = 0
            max_chars = 1000

            for element in elements:
                # Only detect from text content (paragraphs, headings)
                if element.element_type in (
                    ElementType.PARAGRAPH,
                    ElementType.NARRATIVE_TEXT,
                    ElementType.HEADING,
                    ElementType.TITLE,
                ):
                    sample_texts.append(element.content)
                    total_chars += len(element.content)
                    if total_chars >= max_chars:
                        break

            if not sample_texts:
                return []

            # Combine samples
            combined_text = " ".join(sample_texts)[:max_chars]

            # Detect language
            # #ASSUME: Language Detection: Single language detection sufficient
            # #VERIFY: May need multi-language detection for multilingual docs
            try:
                detected_lang = detect(combined_text)
                logger.debug(f"Detected language: {detected_lang}")
                return [detected_lang]
            except LangDetectException:
                logger.warning("Language detection failed - insufficient text")
                return []

        except ImportError:
            logger.debug("langdetect not installed, skipping language detection")
            return []
        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
            return []

    def _enhance_element_metadata(
        self,
        elements: list[DocumentElement],
        marker_metadata: dict[str, Any],
    ) -> list[DocumentElement]:
        """Enhance element metadata with additional information.

        # Fix 4: Add confidence scores and improve metadata fields

        Args:
            elements (list[DocumentElement]): List of document elements.
            marker_metadata (dict[str, Any]): Metadata from Marker.

        Returns:
            list[DocumentElement]: Enhanced list of document elements.
        """
        # Build hierarchy for parent_id assignment
        heading_stack: list[tuple[int, DocumentElement]] = []  # (level, element)

        for i, element in enumerate(elements):
            # Fix: Add confidence score based on element type
            # #ASSUME: Confidence Estimation: Element type indicates extraction confidence
            # #VERIFY: May need actual ML model confidence if available
            confidence = self._estimate_confidence(element)
            element.metadata.detection_class_prob = confidence

            # Fix: Assign category_depth for headings/titles
            if element.element_type == ElementType.TITLE:
                element.metadata.category_depth = 1
                heading_stack = [(1, element)]  # Reset stack with title
            elif element.element_type == ElementType.HEADING:
                # Simple heuristic: assume level 2 for all headings
                # (can be refined with font size analysis)
                element.metadata.category_depth = 2
                # Pop headings of same or higher level
                while heading_stack and heading_stack[-1][0] >= 2:
                    heading_stack.pop()
                heading_stack.append((2, element))

            # Fix: Assign parent_id based on heading hierarchy
            if element.element_type in (
                ElementType.PARAGRAPH,
                ElementType.NARRATIVE_TEXT,
                ElementType.TABLE,
                ElementType.FORMULA,
                ElementType.LIST,
            ):
                # Assign to most recent heading
                if heading_stack:
                    element.metadata.parent_id = heading_stack[-1][1].metadata.element_id

            # Note: coordinates would require position info from Marker
            # Marker's current API doesn't provide bounding boxes in structured form
            # This would need additional integration with Marker's layout detection

        return elements

    def _estimate_confidence(self, element: DocumentElement) -> float:
        """Estimate confidence score for element extraction.

        # #ASSUME: Confidence Heuristics: Element properties indicate quality
        # #VERIFY: Compare with actual extraction accuracy metrics

        Args:
            element (DocumentElement): Document element.

        Returns:
            float: Confidence score between 0.0 and 1.0.
        """
        # Base confidence by element type
        type_confidence = {
            ElementType.FORMULA: 0.95,  # LaTeX formulas are high confidence
            ElementType.TABLE: 0.90,  # Marker excels at tables
            ElementType.TITLE: 0.95,  # Clear structure
            ElementType.HEADING: 0.90,
            ElementType.PARAGRAPH: 0.85,
            ElementType.NARRATIVE_TEXT: 0.85,
            ElementType.LIST: 0.85,
        }

        base_confidence = type_confidence.get(element.element_type, 0.80)

        # Adjust based on content length (very short elements may be misclassified)
        content_length = len(element.content.strip())
        if content_length < 5:
            base_confidence *= 0.7  # Reduce confidence for very short content
        elif content_length > 100:
            base_confidence = min(base_confidence + 0.05, 1.0)  # Boost for substantial content

        return round(base_confidence, 2)

    def get_priority(self) -> int:
        """Get parser priority.

        Marker has high priority (10) due to superior quality,
        but falls back to simpler parsers on failure.

        Returns:
            int: Priority value (10 = high priority).
        """
        return cast(int, self.config.get("priority", 10))
