"""PDF parser implementations."""

import logging
import time
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from data_ingestor.core.base import BaseParser
from data_ingestor.core.exceptions import ParserError
from data_ingestor.core.models import Document, DocumentElement, DocumentFormat, ElementType, ParserResult

logger = logging.getLogger(__name__)


class PyMuPDFParser(BaseParser):
    """PDF parser using PyMuPDF library."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize PyMuPDF parser.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        self.name = "PyMuPDFParser"

    def supports_format(self, document_format: DocumentFormat) -> bool:
        """Check if this parser supports PDF format.

        Args:
            document_format: Format to check

        Returns:
            True if PDF, False otherwise
        """
        return document_format == DocumentFormat.PDF

    def parse(self, document: Document) -> ParserResult:
        """Parse PDF document and extract text and structure.

        # #CRITICAL: Memory Management: Large PDFs can exhaust memory
        # #VERIFY: Process page-by-page to limit memory usage

        Args:
            document: Document to parse

        Returns:
            ParserResult with extracted elements

        Raises:
            ParserError: If parsing fails
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
                                    metadata={"font_size": font_size},
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
            pdf_doc: PyMuPDF document object

        Returns:
            Dictionary with metadata
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
            text: Text content
            font_size: Font size in points

        Returns:
            Classified element type
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
            True if operational
        """
        try:
            # Try to access PyMuPDF version
            _ = fitz.version
            return True
        except Exception as e:
            logger.error(f"PyMuPDF health check failed: {e}")
            return False


class PyMuPDF4LLMParser(BaseParser):
    """PDF parser using PyMuPDF4LLM for LLM-optimized extraction."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize PyMuPDF4LLM parser.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        self.name = "PyMuPDF4LLMParser"

    def supports_format(self, document_format: DocumentFormat) -> bool:
        """Check if this parser supports PDF format.

        Args:
            document_format: Format to check

        Returns:
            True if PDF, False otherwise
        """
        return document_format == DocumentFormat.PDF

    def parse(self, document: Document) -> ParserResult:
        """Parse PDF using PyMuPDF4LLM for better structure preservation.

        # #CRITICAL: Library Dependency: pymupdf4llm may not be installed
        # #VERIFY: Gracefully degrade if library unavailable

        Args:
            document: Document to parse

        Returns:
            ParserResult with extracted elements

        Raises:
            ParserError: If parsing fails
        """
        if not document.source_path:
            raise ParserError(
                message="Source path required for PDF parsing",
                parser_name=self.name,
            )

        start_time = time.time()

        try:
            import pymupdf4llm

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
            markdown: Markdown text

        Returns:
            List of document elements
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
            True if operational
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
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize Marker parser.

        # #CRITICAL: GPU Availability: Marker performs best with GPU
        # #VERIFY: Must detect GPU and configure appropriately

        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        self.name = "MarkerParser"
        self._marker_available = False
        self._gpu_available = False

        # Check availability
        try:
            import marker  # noqa: F401

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
            document_format: Format to check

        Returns:
            True if PDF and Marker is available, False otherwise
        """
        return document_format == DocumentFormat.PDF and self._marker_available

    def parse(self, document: Document) -> ParserResult:
        """Parse PDF using Marker for high-quality extraction.

        # #CRITICAL: Memory Management: Marker loads models which consume significant memory
        # #VERIFY: Monitor memory usage and implement resource limits

        # #CRITICAL: Processing Time: Marker is slower than simple parsers
        # #VERIFY: Consider async processing or timeout limits

        Args:
            document: Document to parse

        Returns:
            ParserResult with extracted elements

        Raises:
            ParserError: If parsing fails
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
            from marker.convert import convert_single_pdf
            from marker.models import load_all_models

            # Load Marker models
            # #CRITICAL: Model Loading: First-time model download can take minutes
            # #VERIFY: Implement model caching and pre-loading strategy
            logger.info("Loading Marker models...")
            model_lst = load_all_models()

            # Convert PDF to markdown
            # #ASSUME: Marker Configuration: Default configuration suitable for most PDFs
            # #VERIFY: May need custom config for specific document types
            logger.info(f"Processing {Path(document.source_path).name} with Marker...")

            full_text, images, metadata = convert_single_pdf(
                document.source_path,
                model_lst,
                max_pages=self.config.get("max_pages"),  # None = all pages
                langs=self.config.get("ocr_languages", ["English"]),
            )

            # Convert markdown to elements
            elements = self._markdown_to_elements(full_text)

            # Enhance metadata
            enhanced_metadata = {
                "page_count": metadata.get("pages", 0),
                "toc": metadata.get("toc", []),
                "languages": metadata.get("languages", []),
                "images_extracted": len(images),
                "marker_version": metadata.get("version", "unknown"),
                "gpu_used": self._gpu_available,
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

    def _markdown_to_elements(self, markdown: str) -> list[DocumentElement]:
        """Convert Marker's markdown output to document elements.

        # #ASSUME: Markdown Format: Marker's markdown format is consistent
        # #VERIFY: May need more sophisticated parsing for complex structures

        Args:
            markdown: Markdown text from Marker

        Returns:
            List of document elements
        """
        elements: list[DocumentElement] = []
        lines = markdown.split("\n")

        in_table = False
        table_lines: list[str] = []

        for line in lines:
            line_stripped = line.strip()

            if not line_stripped:
                # Flush table if we were in one
                if in_table and table_lines:
                    table_content = "\n".join(table_lines)
                    element = DocumentElement(element_type=ElementType.TABLE, content=table_content)
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
                element = DocumentElement(element_type=ElementType.TABLE, content=table_content)
                elements.append(element)
                table_lines = []
                in_table = False

            # Detect formulas (LaTeX in $$...$$)
            if line_stripped.startswith("$$") and line_stripped.endswith("$$"):
                content = line_stripped[2:-2].strip()
                element = DocumentElement(element_type=ElementType.FORMULA, content=content)
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
                element = DocumentElement(element_type=element_type, content=content)
                elements.append(element)

        # Flush any remaining table
        if in_table and table_lines:
            table_content = "\n".join(table_lines)
            element = DocumentElement(element_type=ElementType.TABLE, content=table_content)
            elements.append(element)

        return elements

    def health_check(self) -> bool:
        """Check if Marker is available and operational.

        Returns:
            True if operational
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

    def get_priority(self) -> int:
        """Get parser priority.

        Marker has high priority (10) due to superior quality,
        but falls back to simpler parsers on failure.

        Returns:
            Priority value (10 = high priority)
        """
        return self.config.get("priority", 10)
