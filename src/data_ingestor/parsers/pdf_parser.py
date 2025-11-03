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
