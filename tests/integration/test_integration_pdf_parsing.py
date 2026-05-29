"""Integration tests for PDF parsing with real PDF files (no mocks)."""

import json
from pathlib import Path
from typing import Any

import pytest

from data_ingestor.core.models import Document, DocumentFormat, ElementType
from data_ingestor.parsers.pdf_parser import PyMuPDF4LLMParser, PyMuPDFParser


class TestPDFParsingIntegration:
    """Integration tests using real PDF files and validation data."""

    @pytest.fixture
    def test_pdfs_dir(self) -> Path:
        """Get the test PDFs directory."""
        path = Path("data/test_pdfs")
        if not path.exists() or not any(path.glob("*.pdf")):
            pytest.skip("Sample test PDFs not available in data/test_pdfs")
        return path

    @pytest.fixture
    def validation_dir(self) -> Path:
        """Get the validation directory."""
        path = Path("data/test_pdfs/validation")
        if not path.exists():
            pytest.skip("PDF validation data not available in data/test_pdfs/validation")
        return path

    def load_validation_data(self, validation_dir: Path, pdf_name: str) -> dict[str, Any]:
        """Load validation data for a PDF file."""
        validation_file = validation_dir / f"{pdf_name}.json"
        if not validation_file.exists():
            pytest.skip(f"Validation data not available: {validation_file}")
        with open(validation_file) as f:
            return json.load(f)

    def test_pymupdf_parser_simple_text(self, test_pdfs_dir: Path, validation_dir: Path) -> None:
        """Test PyMuPDF parser with simple text PDF."""
        pdf_path = test_pdfs_dir / "01_simple_text.pdf"
        validation = self.load_validation_data(validation_dir, "01_simple_text")

        doc = Document(source_path=str(pdf_path), format=DocumentFormat.PDF)
        parser = PyMuPDFParser()
        result = parser.parse(doc)

        assert result.success is True
        assert len(result.elements) > 0

        # Verify page count
        pages = {elem.page_number for elem in result.elements if elem.page_number}
        assert len(pages) == validation["metadata"]["expected_pages"]

        # Verify word count range
        full_text = " ".join(elem.content for elem in result.elements)
        word_count = len(full_text.split())
        assert validation["metadata"]["expected_word_count_min"] <= word_count <= \
               validation["metadata"]["expected_word_count_max"]

        # Verify required phrases
        for phrase in validation["content_validation"]["required_phrases"]:
            assert phrase in full_text, f"Missing: {phrase}"

    def test_pymupdf4llm_parser_simple_text(self, test_pdfs_dir: Path, validation_dir: Path) -> None:
        """Test PyMuPDF4LLM parser with simple text PDF."""
        pdf_path = test_pdfs_dir / "01_simple_text.pdf"
        validation = self.load_validation_data(validation_dir, "01_simple_text")

        doc = Document(source_path=str(pdf_path), format=DocumentFormat.PDF)
        parser = PyMuPDF4LLMParser()
        result = parser.parse(doc)

        assert result.success is True
        assert len(result.elements) > 0

        # Verify required keywords
        full_text = " ".join(elem.content for elem in result.elements)
        for keyword in validation["content_validation"]["required_keywords"]:
            assert keyword.lower() in full_text.lower(), f"Missing: {keyword}"

    def test_pymupdf_parser_multipage_document(self, test_pdfs_dir: Path, validation_dir: Path) -> None:
        """Test PyMuPDF parser with multipage PDF."""
        pdf_path = test_pdfs_dir / "02_multipage_document.pdf"
        validation = self.load_validation_data(validation_dir, "02_multipage_document")

        doc = Document(source_path=str(pdf_path), format=DocumentFormat.PDF)
        parser = PyMuPDFParser()
        result = parser.parse(doc)

        assert result.success is True

        # Verify page count
        pages = {elem.page_number for elem in result.elements if elem.page_number}
        assert len(pages) == validation["metadata"]["expected_pages"]

        # Verify content from different pages
        full_text = " ".join(elem.content for elem in result.elements)
        for phrase in validation["content_validation"]["required_phrases"]:
            assert phrase in full_text, f"Missing: {phrase}"

    def test_pymupdf_parser_tabular_data(self, test_pdfs_dir: Path, validation_dir: Path) -> None:
        """Test PyMuPDF parser with tabular data PDF."""
        pdf_path = test_pdfs_dir / "04_tabular_data.pdf"
        validation = self.load_validation_data(validation_dir, "04_tabular_data")

        doc = Document(source_path=str(pdf_path), format=DocumentFormat.PDF)
        parser = PyMuPDFParser()
        result = parser.parse(doc)

        assert result.success is True
        assert len(result.elements) > 0

        # Verify required content
        full_text = " ".join(elem.content for elem in result.elements)
        for phrase in validation["content_validation"]["required_phrases"]:
            assert phrase in full_text, f"Missing: {phrase}"

    def test_parser_consistency_across_parsers(self, test_pdfs_dir: Path, validation_dir: Path) -> None:
        """Test that different parsers produce consistent results."""
        pdf_path = test_pdfs_dir / "01_simple_text.pdf"
        validation = self.load_validation_data(validation_dir, "01_simple_text")

        # Parse with both parsers
        doc1 = Document(source_path=str(pdf_path), format=DocumentFormat.PDF)
        doc2 = Document(source_path=str(pdf_path), format=DocumentFormat.PDF)

        pymupdf_result = PyMuPDFParser().parse(doc1)
        pymupdf4llm_result = PyMuPDF4LLMParser().parse(doc2)

        # Both should succeed
        assert pymupdf_result.success is True
        assert pymupdf4llm_result.success is True

        # Both should extract content
        pymupdf_text = " ".join(elem.content for elem in pymupdf_result.elements)
        pymupdf4llm_text = " ".join(elem.content for elem in pymupdf4llm_result.elements)

        # Both should contain required keywords
        for keyword in validation["content_validation"]["required_keywords"]:
            assert keyword.lower() in pymupdf_text.lower() or \
                   keyword.lower() in pymupdf4llm_text.lower(), f"Missing: {keyword}"

    def test_mixed_content_parsing(self, test_pdfs_dir: Path, validation_dir: Path) -> None:
        """Test parsing PDF with mixed content types."""
        pdf_path = test_pdfs_dir / "05_mixed_content.pdf"
        validation = self.load_validation_data(validation_dir, "05_mixed_content")

        doc = Document(source_path=str(pdf_path), format=DocumentFormat.PDF)
        parser = PyMuPDFParser()
        result = parser.parse(doc)

        assert result.success is True
        assert len(result.elements) > 0

        # Verify required content
        full_text = " ".join(elem.content for elem in result.elements)
        for phrase in validation["content_validation"]["required_phrases"]:
            assert phrase in full_text, f"Missing: {phrase}"

        # Verify multiple element types
        element_types = {elem.element_type for elem in result.elements}
        assert len(element_types) > 1


class TestPDFParsingEdgeCases:
    """Test edge cases in PDF parsing with real files."""

    @pytest.fixture
    def test_pdfs_dir(self) -> Path:
        """Get the test PDFs directory."""
        path = Path("data/test_pdfs")
        if not path.exists() or not any(path.glob("*.pdf")):
            pytest.skip("Sample test PDFs not available in data/test_pdfs")
        return path

    @pytest.fixture
    def validation_dir(self) -> Path:
        """Get the validation directory."""
        path = Path("data/test_pdfs/validation")
        if not path.exists():
            pytest.skip("PDF validation data not available in data/test_pdfs/validation")
        return path

    def test_large_pdf_processing(self, test_pdfs_dir: Path) -> None:
        """Test processing larger PDF files."""
        pdf_path = test_pdfs_dir / "Where-does-wind-matter.pdf"

        if not pdf_path.exists():
            pytest.skip("Large PDF file not found")

        doc = Document(source_path=str(pdf_path), format=DocumentFormat.PDF)
        parser = PyMuPDFParser()
        result = parser.parse(doc)

        assert result.success is True
        assert len(result.elements) > 0

        # Verify multi-page content
        pages = {elem.page_number for elem in result.elements if elem.page_number}
        assert len(pages) > 1

    def test_complex_layout_parsing(self, test_pdfs_dir: Path, validation_dir: Path) -> None:
        """Test parsing PDF with complex layout."""
        pdf_path = test_pdfs_dir / "06_complex_layout.pdf"
        validation = self.load_validation_data(validation_dir, "06_complex_layout")

        doc = Document(source_path=str(pdf_path), format=DocumentFormat.PDF)
        parser = PyMuPDFParser()
        result = parser.parse(doc)

        assert result.success is True
        assert len(result.elements) > 0

        # Verify required content
        full_text = " ".join(elem.content for elem in result.elements)
        for phrase in validation["content_validation"]["required_phrases"]:
            assert phrase in full_text, f"Missing: {phrase}"

    def test_formatted_text_preservation(self, test_pdfs_dir: Path, validation_dir: Path) -> None:
        """Test that formatted text is properly preserved."""
        pdf_path = test_pdfs_dir / "03_formatted_text.pdf"
        validation = self.load_validation_data(validation_dir, "03_formatted_text")

        doc = Document(source_path=str(pdf_path), format=DocumentFormat.PDF)
        parser = PyMuPDFParser()
        result = parser.parse(doc)

        assert result.success is True

        # Verify required phrases
        full_text = " ".join(elem.content for elem in result.elements)
        for phrase in validation["content_validation"]["required_phrases"]:
            assert phrase in full_text, f"Missing: {phrase}"

    def load_validation_data(self, validation_dir: Path, pdf_name: str) -> dict[str, Any]:
        """Load validation data for a PDF file."""
        validation_file = validation_dir / f"{pdf_name}.json"
        if not validation_file.exists():
            pytest.skip(f"Validation data not available: {validation_file}")
        with open(validation_file) as f:
            return json.load(f)
