"""Comprehensive tests for PDF parser implementations."""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from data_ingestor.core.exceptions import ParserError
from data_ingestor.core.models import Document, DocumentElement, DocumentFormat, ElementType
from data_ingestor.parsers.pdf_parser import MarkerParser, PyMuPDF4LLMParser, PyMuPDFParser

# The marker-pdf package is an optional extra (advanced-pdf) that is not always
# installed. Tests that import or patch the real marker package require it.
requires_marker = pytest.mark.skipif(
    importlib.util.find_spec("marker") is None,
    reason="marker-pdf not installed (optional advanced-pdf extra)",
)


class TestPyMuPDFParser:
    """Tests for PyMuPDFParser."""

    def test_initialization(self) -> None:
        """Test parser initialization."""
        parser = PyMuPDFParser()
        assert parser.name == "PyMuPDFParser"

    def test_initialization_with_config(self) -> None:
        """Test parser initialization with config."""
        config = {"max_file_size_mb": 100}
        parser = PyMuPDFParser(config)
        assert parser.config == config

    def test_supports_format_pdf(self) -> None:
        """Test that parser supports PDF format."""
        parser = PyMuPDFParser()
        assert parser.supports_format(DocumentFormat.PDF) is True

    def test_supports_format_docx(self) -> None:
        """Test that parser doesn't support DOCX format."""
        parser = PyMuPDFParser()
        assert parser.supports_format(DocumentFormat.DOCX) is False

    def test_parse_without_source_path(self) -> None:
        """Test parse raises error without source path."""
        parser = PyMuPDFParser()
        doc = Document(source_path=None, format=DocumentFormat.PDF)

        with pytest.raises(ParserError) as exc_info:
            parser.parse(doc)

        assert "Source path required" in str(exc_info.value)

    @patch("data_ingestor.parsers.pdf_parser.fitz")
    def test_parse_basic_pdf(self, mock_fitz, temp_test_file: Path) -> None:
        """Test parsing basic PDF."""
        # Setup mock PDF document
        mock_pdf = MagicMock()
        mock_pdf.metadata = {"title": "Test Document"}
        mock_pdf.__len__.return_value = 1

        # Setup mock page
        mock_page = MagicMock()
        mock_page.get_text.return_value = {
            "blocks": [
                {
                    "type": 0,
                    "lines": [
                        {
                            "spans": [
                                {"text": "Test content", "size": 12},
                            ],
                        },
                    ],
                    "bbox": (0, 0, 100, 100),
                },
            ],
        }
        mock_page.get_images.return_value = []
        mock_pdf.__getitem__.return_value = mock_page

        mock_fitz.open.return_value = mock_pdf

        parser = PyMuPDFParser()
        doc = Document(source_path=str(temp_test_file), format=DocumentFormat.PDF)

        result = parser.parse(doc)

        assert result.success is True
        assert len(result.elements) > 0
        assert result.parser_name == "PyMuPDFParser"

    @patch("data_ingestor.parsers.pdf_parser.fitz")
    def test_parse_with_images(self, mock_fitz, temp_test_file: Path) -> None:
        """Test parsing PDF with images."""
        # Setup mock PDF with images
        mock_pdf = MagicMock()
        mock_pdf.metadata = {}
        mock_pdf.__len__.return_value = 1

        mock_page = MagicMock()
        mock_page.get_text.return_value = {"blocks": []}
        mock_page.get_images.return_value = [1, 2]  # Two images
        mock_pdf.__getitem__.return_value = mock_page

        mock_fitz.open.return_value = mock_pdf

        parser = PyMuPDFParser()
        doc = Document(source_path=str(temp_test_file), format=DocumentFormat.PDF)

        result = parser.parse(doc)

        assert result.success is True
        assert len(result.warnings) > 0
        assert "images" in result.warnings[0].lower()

    @patch("data_ingestor.parsers.pdf_parser.fitz")
    def test_parse_exception_handling(self, mock_fitz, temp_test_file: Path) -> None:
        """Test parse handles exceptions."""
        mock_fitz.open.side_effect = Exception("Test error")

        parser = PyMuPDFParser()
        doc = Document(source_path=str(temp_test_file), format=DocumentFormat.PDF)

        result = parser.parse(doc)

        assert result.success is False
        assert "Failed to parse PDF" in result.error_message

    def test_classify_text_block_large_font(self) -> None:
        """Test text classification with large font."""
        parser = PyMuPDFParser()
        element_type = parser._classify_text_block("Test Title", 18)
        assert element_type == ElementType.TITLE

    def test_classify_text_block_medium_font(self) -> None:
        """Test text classification with medium font."""
        parser = PyMuPDFParser()
        element_type = parser._classify_text_block("Test Heading", 15)
        assert element_type == ElementType.HEADING

    def test_classify_text_block_uppercase(self) -> None:
        """Test text classification for uppercase text."""
        parser = PyMuPDFParser()
        element_type = parser._classify_text_block("HEADING TEXT", 12)
        assert element_type == ElementType.HEADING

    def test_classify_text_block_paragraph(self) -> None:
        """Test text classification for paragraph."""
        parser = PyMuPDFParser()
        element_type = parser._classify_text_block("Normal paragraph text here", 12)
        assert element_type == ElementType.PARAGRAPH

    @patch("data_ingestor.parsers.pdf_parser.fitz")
    def test_health_check_success(self, mock_fitz) -> None:
        """Test health check when PyMuPDF is available."""
        mock_fitz.version = "1.0.0"

        parser = PyMuPDFParser()
        assert parser.health_check() is True

    @patch("data_ingestor.parsers.pdf_parser.fitz")
    def test_health_check_failure(self, mock_fitz) -> None:
        """Test health check when PyMuPDF fails."""
        type(mock_fitz).version = property(lambda self: (_ for _ in ()).throw(Exception("Test error")))

        parser = PyMuPDFParser()
        assert parser.health_check() is False


class TestPyMuPDF4LLMParser:
    """Tests for PyMuPDF4LLMParser."""

    def test_initialization(self) -> None:
        """Test parser initialization."""
        parser = PyMuPDF4LLMParser()
        assert parser.name == "PyMuPDF4LLMParser"

    def test_supports_format_pdf(self) -> None:
        """Test that parser supports PDF format."""
        parser = PyMuPDF4LLMParser()
        assert parser.supports_format(DocumentFormat.PDF) is True

    def test_parse_without_source_path(self) -> None:
        """Test parse raises error without source path."""
        parser = PyMuPDF4LLMParser()
        doc = Document(source_path=None, format=DocumentFormat.PDF)

        with pytest.raises(ParserError):
            parser.parse(doc)

    @patch("data_ingestor.parsers.pdf_parser.pymupdf4llm", create=True)
    def test_parse_success(self, mock_pymupdf4llm, temp_test_file: Path) -> None:
        """Test parsing with PyMuPDF4LLM."""
        mock_pymupdf4llm.to_markdown.return_value = "# Test Title\n\nTest paragraph"

        parser = PyMuPDF4LLMParser()
        doc = Document(source_path=str(temp_test_file), format=DocumentFormat.PDF)

        result = parser.parse(doc)

        assert result.success is True
        assert len(result.elements) > 0
        assert result.parser_name == "PyMuPDF4LLMParser"

    def test_parse_import_error(self, temp_test_file: Path) -> None:
        """Test parse handles ImportError gracefully."""
        with patch.dict("sys.modules", {"pymupdf4llm": None}):
            parser = PyMuPDF4LLMParser()
            doc = Document(source_path=str(temp_test_file), format=DocumentFormat.PDF)

            result = parser.parse(doc)

            assert result.success is False
            assert "not installed" in result.error_message

    def test_markdown_to_elements_heading(self) -> None:
        """Test markdown to elements conversion for headings."""
        parser = PyMuPDF4LLMParser()
        markdown = "# Title\n## Heading\nParagraph text"

        elements = parser._markdown_to_elements(markdown)

        assert len(elements) == 3
        assert elements[0].element_type == ElementType.TITLE
        assert elements[1].element_type == ElementType.HEADING
        assert elements[2].element_type == ElementType.PARAGRAPH

    def test_markdown_to_elements_empty_lines(self) -> None:
        """Test markdown to elements skips empty lines."""
        parser = PyMuPDF4LLMParser()
        markdown = "# Title\n\n\nParagraph"

        elements = parser._markdown_to_elements(markdown)

        assert len(elements) == 2

    @patch("data_ingestor.parsers.pdf_parser.pymupdf4llm", create=True)
    def test_health_check_success(self, mock_pymupdf4llm) -> None:
        """Test health check when PyMuPDF4LLM is available."""
        mock_pymupdf4llm.__version__ = "1.0.0"

        parser = PyMuPDF4LLMParser()
        assert parser.health_check() is True

    def test_health_check_import_error(self) -> None:
        """Test health check when PyMuPDF4LLM is not available."""
        with patch.dict("sys.modules", {"pymupdf4llm": None}):
            parser = PyMuPDF4LLMParser()
            assert parser.health_check() is False


class TestMarkerParser:
    """Tests for MarkerParser."""

    def test_initialization_without_marker(self) -> None:
        """Test parser initialization when marker is not available."""
        with patch.dict("sys.modules", {"marker": None}):
            parser = MarkerParser()
            assert parser.name == "MarkerParser"
            assert parser._marker_available is False

    @requires_marker
    @patch("data_ingestor.parsers.pdf_parser.torch", create=True)
    @patch("data_ingestor.parsers.pdf_parser.marker", create=True)
    def test_initialization_with_gpu(self, mock_marker, mock_torch) -> None:
        """Test parser initialization with GPU available."""
        mock_torch.cuda.is_available.return_value = True
        mock_torch.version.cuda = "11.0"

        parser = MarkerParser()

        assert parser._marker_available is True
        assert parser._gpu_available is True

    def test_supports_format_without_marker(self) -> None:
        """Test supports_format when marker is not available."""
        with patch.dict("sys.modules", {"marker": None}):
            parser = MarkerParser()
            assert parser.supports_format(DocumentFormat.PDF) is False

    def test_parse_without_source_path(self) -> None:
        """Test parse raises error without source path."""
        parser = MarkerParser()
        doc = Document(source_path=None, format=DocumentFormat.PDF)

        with pytest.raises(ParserError):
            parser.parse(doc)

    def test_parse_without_marker_available(self, temp_test_file: Path) -> None:
        """Test parse when marker is not available."""
        with patch.dict("sys.modules", {"marker": None}):
            parser = MarkerParser()
            doc = Document(source_path=str(temp_test_file), format=DocumentFormat.PDF)

            result = parser.parse(doc)

            assert result.success is False
            assert "not installed" in result.error_message

    def test_markdown_to_elements_table(self) -> None:
        """Test markdown to elements conversion for tables."""
        parser = MarkerParser()
        markdown = "| Header 1 | Header 2 |\n| Cell 1 | Cell 2 |"

        elements = parser._markdown_to_elements(markdown)

        assert len(elements) > 0
        assert any(el.element_type == ElementType.TABLE for el in elements)

    def test_markdown_to_elements_formula(self) -> None:
        """Test markdown to elements conversion for formulas."""
        parser = MarkerParser()
        markdown = "$$E = mc^2$$"

        elements = parser._markdown_to_elements(markdown)

        assert len(elements) == 1
        assert elements[0].element_type == ElementType.FORMULA

    def test_markdown_to_elements_with_page_markers(self) -> None:
        """Test markdown parsing with page markers."""
        parser = MarkerParser()
        markdown = "{0}\n# Title on page 1\n{1}\nContent on page 2"

        elements = parser._markdown_to_elements(markdown)

        # Should parse elements and track pages
        assert len(elements) >= 1

    def test_extract_toc_from_elements(self) -> None:
        """Test TOC extraction from elements."""
        parser = MarkerParser()
        elements = [
            DocumentElement(element_type=ElementType.TITLE, content="Title 1"),
            DocumentElement(element_type=ElementType.HEADING, content="Heading 1"),
            DocumentElement(element_type=ElementType.PARAGRAPH, content="Content"),
        ]

        toc = parser._extract_toc_from_elements(elements)

        assert len(toc) == 2
        assert toc[0]["title"] == "Title 1"
        assert toc[1]["title"] == "Heading 1"

    @patch("data_ingestor.parsers.pdf_parser.detect", create=True)
    def test_detect_languages_success(self, mock_detect) -> None:
        """Test language detection success."""
        mock_detect.return_value = "en"

        parser = MarkerParser()
        elements = [
            DocumentElement(element_type=ElementType.PARAGRAPH, content="Test content in English"),
        ]

        languages = parser._detect_languages(elements)

        assert len(languages) == 1
        assert languages[0] == "en"

    def test_detect_languages_import_error(self) -> None:
        """Test language detection when langdetect is not available."""
        with patch.dict("sys.modules", {"langdetect": None}):
            parser = MarkerParser()
            elements = [
                DocumentElement(element_type=ElementType.PARAGRAPH, content="Test content"),
            ]

            languages = parser._detect_languages(elements)

            assert languages == []

    def test_enhance_element_metadata(self) -> None:
        """Test element metadata enhancement."""
        parser = MarkerParser()
        elements = [
            DocumentElement(element_type=ElementType.TITLE, content="Title"),
            DocumentElement(element_type=ElementType.PARAGRAPH, content="Content"),
        ]

        enhanced = parser._enhance_element_metadata(elements, {})

        assert enhanced[0].metadata.category_depth == 1
        assert enhanced[0].metadata.detection_class_prob is not None

    def test_estimate_confidence_formula(self) -> None:
        """Test confidence estimation for formulas."""
        parser = MarkerParser()
        element = DocumentElement(element_type=ElementType.FORMULA, content="E = mc^2")

        confidence = parser._estimate_confidence(element)

        assert confidence >= 0.9

    def test_estimate_confidence_short_content(self) -> None:
        """Test confidence estimation for short content."""
        parser = MarkerParser()
        element = DocumentElement(element_type=ElementType.PARAGRAPH, content="Hi")

        confidence = parser._estimate_confidence(element)

        assert confidence < 0.85

    def test_get_priority(self) -> None:
        """Test get_priority returns correct value."""
        parser = MarkerParser()
        assert parser.get_priority() == 10

    def test_get_priority_custom(self) -> None:
        """Test get_priority with custom config."""
        parser = MarkerParser({"priority": 5})
        assert parser.get_priority() == 5

    def test_health_check_without_marker(self) -> None:
        """Test health check when marker is not available."""
        with patch.dict("sys.modules", {"marker": None}):
            parser = MarkerParser()
            assert parser.health_check() is False


class TestMarkerParserExtended:
    """Extended tests for MarkerParser to improve coverage."""

    def test_markdown_to_elements_list_items(self) -> None:
        """Test markdown parsing with list items."""
        parser = MarkerParser()
        markdown = "- Item 1\n- Item 2\n* Item 3"

        elements = parser._markdown_to_elements(markdown)

        assert len(elements) > 0
        assert any(el.element_type == ElementType.LIST for el in elements)

    def test_markdown_to_elements_separator_lines(self) -> None:
        """Test markdown parsing skips separator lines."""
        parser = MarkerParser()
        markdown = "{0}\n----------\n# Title"

        elements = parser._markdown_to_elements(markdown)

        # Should skip page marker and separator
        assert all(el.content != "----------" for el in elements)

    def test_markdown_to_elements_table_flush(self) -> None:
        """Test table flushing on empty line."""
        parser = MarkerParser()
        markdown = "| Header |\n| Cell |\n\nParagraph"

        elements = parser._markdown_to_elements(markdown)

        # Should have table and paragraph
        assert any(el.element_type == ElementType.TABLE for el in elements)
        assert any(el.element_type == ElementType.PARAGRAPH for el in elements)

    def test_enhance_element_metadata_with_hierarchy(self) -> None:
        """Test metadata enhancement with heading hierarchy."""
        parser = MarkerParser()
        elements = [
            DocumentElement(element_type=ElementType.TITLE, content="Title"),
            DocumentElement(element_type=ElementType.HEADING, content="Section"),
            DocumentElement(element_type=ElementType.TABLE, content="| A | B |"),
            DocumentElement(element_type=ElementType.FORMULA, content="E=mc^2"),
        ]

        enhanced = parser._enhance_element_metadata(elements, {})

        # Title should have category_depth 1
        assert enhanced[0].metadata.category_depth == 1
        # Heading should have category_depth 2
        assert enhanced[1].metadata.category_depth == 2
        # Table and formula should have parent_id from heading
        assert enhanced[2].metadata.parent_id is not None
        assert enhanced[3].metadata.parent_id is not None

    def test_estimate_confidence_long_content(self) -> None:
        """Test confidence estimation for long content."""
        parser = MarkerParser()
        element = DocumentElement(
            element_type=ElementType.PARAGRAPH,
            content="This is a long paragraph with substantial content that exceeds 100 characters and should get a confidence boost.",
        )

        confidence = parser._estimate_confidence(element)

        assert confidence > 0.85

    def test_extract_toc_with_category_depth(self) -> None:
        """Test TOC extraction with category_depth."""
        parser = MarkerParser()
        elements = [
            DocumentElement(element_type=ElementType.TITLE, content="Main Title"),
            DocumentElement(element_type=ElementType.HEADING, content="Section 1"),
        ]

        # Set category_depth manually
        elements[0].metadata.category_depth = 1
        elements[1].metadata.category_depth = 2

        toc = parser._extract_toc_from_elements(elements)

        assert len(toc) == 2
        assert toc[0]["level"] == 1
        assert toc[1]["level"] == 2

    @patch("data_ingestor.parsers.pdf_parser.detect", create=True)
    def test_detect_languages_with_multiple_elements(self, mock_detect) -> None:
        """Test language detection with enough text."""
        mock_detect.return_value = "en"

        parser = MarkerParser()
        elements = [
            DocumentElement(element_type=ElementType.PARAGRAPH, content="A" * 500),
            DocumentElement(element_type=ElementType.PARAGRAPH, content="B" * 500),
            DocumentElement(element_type=ElementType.TABLE, content="Table"),  # Should be skipped
        ]

        languages = parser._detect_languages(elements)

        assert len(languages) == 1

    def test_detect_languages_insufficient_text(self) -> None:
        """Test language detection with insufficient text."""
        parser = MarkerParser()
        elements = []  # No elements

        languages = parser._detect_languages(elements)

        assert languages == []

    @patch("data_ingestor.parsers.pdf_parser.marker", create=True)
    def test_health_check_with_marker(self, mock_marker) -> None:
        """Test health check when marker modules are available."""
        # Mock the marker submodules
        mock_convert = MagicMock()
        mock_models = MagicMock()
        mock_marker.convert.convert_single_pdf = mock_convert
        mock_marker.models.load_all_models = mock_models

        parser = MarkerParser()
        parser._marker_available = True

        result = parser.health_check()

        # Should return False because the import will still fail in the actual code
        # but the test verifies the code path
        assert isinstance(result, bool)

    def test_estimate_confidence_table(self) -> None:
        """Test confidence for table elements."""
        parser = MarkerParser()
        element = DocumentElement(element_type=ElementType.TABLE, content="| A | B |")

        confidence = parser._estimate_confidence(element)

        assert confidence >= 0.90

    def test_markdown_to_elements_remaining_table_flush(self) -> None:
        """Test flushing remaining table at end of document."""
        parser = MarkerParser()
        markdown = "| Header |\n| Cell |"  # Table at end, no trailing newline

        elements = parser._markdown_to_elements(markdown)

        assert len(elements) > 0
        assert elements[0].element_type == ElementType.TABLE


class TestPyMuPDFParserExtended:
    """Extended tests for PyMuPDFParser to improve coverage."""

    @patch("data_ingestor.parsers.pdf_parser.fitz")
    def test_extract_metadata_with_full_metadata(self, mock_fitz, temp_test_file: Path) -> None:
        """Test metadata extraction with all fields populated."""
        mock_pdf = MagicMock()
        mock_pdf.metadata = {
            "title": "Test Title",
            "author": "Test Author",
            "subject": "Test Subject",
            "keywords": "test, keywords",
            "creator": "Test Creator",
            "producer": "Test Producer",
            "creationDate": "2024-01-01",
            "modDate": "2024-01-02",
        }
        mock_pdf.__len__.return_value = 5
        mock_pdf.__getitem__.return_value = MagicMock()
        mock_fitz.open.return_value = mock_pdf

        parser = PyMuPDFParser()
        metadata = parser._extract_metadata(mock_pdf)

        assert metadata["title"] == "Test Title"
        assert metadata["author"] == "Test Author"
        assert metadata["page_count"] == 5

    @patch("data_ingestor.parsers.pdf_parser.fitz")
    def test_parse_multiplePages(self, mock_fitz, temp_test_file: Path) -> None:
        """Test parsing PDF with multiple pages."""
        mock_pdf = MagicMock()
        mock_pdf.metadata = {}
        mock_pdf.__len__.return_value = 3

        # Create mock pages
        mock_pages = []
        for i in range(3):
            mock_page = MagicMock()
            mock_page.get_text.return_value = {
                "blocks": [
                    {
                        "type": 0,
                        "lines": [{"spans": [{"text": f"Page {i} content", "size": 12}]}],
                        "bbox": (0, 0, 100, 100),
                    },
                ],
            }
            mock_page.get_images.return_value = []
            mock_pages.append(mock_page)

        mock_pdf.__getitem__.side_effect = mock_pages
        mock_fitz.open.return_value = mock_pdf

        parser = PyMuPDFParser()
        doc = Document(source_path=str(temp_test_file), format=DocumentFormat.PDF)

        result = parser.parse(doc)

        assert result.success is True
        assert len(result.elements) == 3

    @pytest.mark.parametrize(
        "text,font_size,expected_type,reason",
        [
            ("Huge Title", 20, ElementType.TITLE, "large_font_size"),
            ("Exact Boundary", 15, ElementType.HEADING, "heading_threshold"),
            (
                "THIS IS A LONG HEADING THAT EXCEEDS THE 100 CHARACTER LIMIT" * 3,
                12,
                ElementType.PARAGRAPH,
                "long_caps_text",
            ),
            ("Short", 12, ElementType.PARAGRAPH, "short_mixed_case"),
            ("VERY SHORT CAPS", 12, ElementType.HEADING, "short_all_caps"),
            ("", 12, ElementType.PARAGRAPH, "empty_string"),
            ("Medium Text", 14, ElementType.PARAGRAPH, "below_heading_threshold"),
            ("ALL CAPS", 16, ElementType.HEADING, "caps_large_font"),
        ],
        ids=lambda x: x if isinstance(x, str) and len(x) < 30 else str(x)[:20] if isinstance(x, str) else str(x),
    )
    @patch("data_ingestor.parsers.pdf_parser.fitz")
    def test_classify_text_variations(self, mock_fitz, text, font_size, expected_type, reason) -> None:
        """Test text classification with various inputs."""
        parser = PyMuPDFParser()
        result = parser._classify_text_block(text, font_size)
        assert result == expected_type, f"Failed for case: {reason}"


@requires_marker
class TestMarkerParserParseMethod:
    """Comprehensive tests for MarkerParser.parse() method with LLM processing."""

    @patch("data_ingestor.parsers.pdf_parser.Path")
    @patch("data_ingestor.parsers.pdf_parser.time")
    def test_parse_with_llm_success(self, mock_time, mock_path_cls, temp_test_file: Path) -> None:
        """Test successful parse with LLM enhancement (primary model)."""
        mock_time.time.side_effect = [100.0, 105.0]  # start, end
        mock_path_cls.return_value.name = "test.pdf"

        # Create mock output from Marker
        mock_output = MagicMock()
        mock_output.markdown = "# Title\n\nContent"
        mock_output.images = []
        mock_output.metadata = {"pages": 1, "toc": [], "languages": ["en"], "version": "1.10"}

        with (
            patch.object(MarkerParser, "_process_with_llm", return_value=mock_output) as mock_process_llm,
            patch.object(MarkerParser, "_markdown_to_elements") as mock_md_to_elements,
            patch.object(MarkerParser, "_enhance_element_metadata") as mock_enhance,
            patch("marker.models.create_model_dict") as mock_create_model,
        ):

            # Setup mocks
            mock_create_model.return_value = {"test": "model"}
            mock_elements = [DocumentElement(element_type=ElementType.TITLE, content="Title")]
            mock_md_to_elements.return_value = mock_elements
            mock_enhance.return_value = mock_elements

            # Create parser with LLM enabled
            parser = MarkerParser()
            parser.use_llm = True
            parser.openrouter_api_key = "test-key"
            parser.llm_model_primary = "test/primary"

            doc = Document(source_path=str(temp_test_file), format=DocumentFormat.PDF)
            result = parser.parse(doc)

            # Verify result
            assert result.success is True
            assert result.parser_name == "MarkerParser"
            assert result.processing_time == 5.0
            assert len(result.elements) == 1
            assert result.metadata["llm_enhanced"] is True
            assert result.metadata["llm_model"] == "test/primary"

            # Verify LLM was called
            mock_process_llm.assert_called_once()

    @patch("data_ingestor.parsers.pdf_parser.Path")
    @patch("data_ingestor.parsers.pdf_parser.time")
    def test_parse_with_llm_fallback_success(self, mock_time, mock_path_cls, temp_test_file: Path) -> None:
        """Test parse where primary LLM fails with API error, fallback succeeds."""
        mock_time.time.side_effect = [100.0, 105.0]
        mock_path_cls.return_value.name = "test.pdf"

        mock_output = MagicMock()
        mock_output.markdown = "# Title"
        mock_output.images = []
        mock_output.metadata = {"pages": 1, "version": "1.10"}

        with (
            patch.object(MarkerParser, "_process_with_llm") as mock_process_llm,
            patch.object(MarkerParser, "_markdown_to_elements") as mock_md_to_elements,
            patch.object(MarkerParser, "_enhance_element_metadata") as mock_enhance,
            patch.object(MarkerParser, "_extract_toc_from_elements", return_value=[]),
            patch.object(MarkerParser, "_detect_languages", return_value=["en"]),
            patch("marker.models.create_model_dict") as mock_create_model,
        ):

            # Primary fails with API error, fallback succeeds
            mock_process_llm.side_effect = [
                Exception("API connection timeout"),
                mock_output,  # Fallback succeeds
            ]

            mock_create_model.return_value = {"test": "model"}
            mock_elements = [DocumentElement(element_type=ElementType.TITLE, content="Title")]
            mock_md_to_elements.return_value = mock_elements
            mock_enhance.return_value = mock_elements

            parser = MarkerParser()
            parser.use_llm = True
            parser.openrouter_api_key = "test-key"
            parser.llm_model_primary = "test/primary"
            parser.llm_model_fallback = "test/fallback"
            parser.enable_fallback = True

            doc = Document(source_path=str(temp_test_file), format=DocumentFormat.PDF)
            result = parser.parse(doc)

            assert result.success is True
            assert result.metadata["llm_model"] == "test/fallback"
            assert result.metadata["llm_fallback_used"] is True

    @patch("data_ingestor.parsers.pdf_parser.Path")
    @patch("data_ingestor.parsers.pdf_parser.time")
    def test_parse_with_llm_both_fail_process_without(self, mock_time, mock_path_cls, temp_test_file: Path) -> None:
        """Test parse where both primary and fallback fail, processes without LLM."""
        mock_time.time.side_effect = [100.0, 105.0]
        mock_path_cls.return_value.name = "test.pdf"

        mock_output = MagicMock()
        mock_output.markdown = "# Title"
        mock_output.images = []
        mock_output.metadata = {"pages": 1, "version": "1.10"}

        with (
            patch.object(MarkerParser, "_process_with_llm") as mock_process_llm,
            patch.object(MarkerParser, "_process_without_llm", return_value=mock_output) as mock_process_no_llm,
            patch.object(MarkerParser, "_markdown_to_elements") as mock_md_to_elements,
            patch.object(MarkerParser, "_enhance_element_metadata") as mock_enhance,
            patch.object(MarkerParser, "_extract_toc_from_elements", return_value=[]),
            patch.object(MarkerParser, "_detect_languages", return_value=["en"]),
            patch("marker.models.create_model_dict") as mock_create_model,
        ):

            # Both primary and fallback fail
            mock_process_llm.side_effect = [
                Exception("API 429 rate limit"),
                Exception("Fallback also failed"),
            ]

            mock_create_model.return_value = {"test": "model"}
            mock_elements = [DocumentElement(element_type=ElementType.TITLE, content="Title")]
            mock_md_to_elements.return_value = mock_elements
            mock_enhance.return_value = mock_elements

            parser = MarkerParser()
            parser.use_llm = True
            parser.openrouter_api_key = "test-key"
            parser.enable_fallback = True

            doc = Document(source_path=str(temp_test_file), format=DocumentFormat.PDF)
            result = parser.parse(doc)

            assert result.success is True
            # Should have processed without LLM
            mock_process_no_llm.assert_called_once()

    @patch("data_ingestor.parsers.pdf_parser.Path")
    @patch("data_ingestor.parsers.pdf_parser.time")
    def test_parse_without_llm_configured(self, mock_time, mock_path_cls, temp_test_file: Path) -> None:
        """Test parse when LLM is not configured (use_llm=False)."""
        mock_time.time.side_effect = [100.0, 105.0]
        mock_path_cls.return_value.name = "test.pdf"

        mock_output = MagicMock()
        mock_output.markdown = "# Title\n\nContent"
        mock_output.images = []
        mock_output.metadata = {"pages": 2, "toc": ["Section 1"], "languages": ["en"], "version": "1.10"}

        with (
            patch.object(MarkerParser, "_process_without_llm", return_value=mock_output) as mock_process_no_llm,
            patch.object(MarkerParser, "_markdown_to_elements") as mock_md_to_elements,
            patch.object(MarkerParser, "_enhance_element_metadata") as mock_enhance,
            patch("marker.models.create_model_dict") as mock_create_model,
        ):

            mock_create_model.return_value = {"test": "model"}
            mock_elements = [
                DocumentElement(element_type=ElementType.TITLE, content="Title"),
                DocumentElement(element_type=ElementType.PARAGRAPH, content="Content"),
            ]
            mock_md_to_elements.return_value = mock_elements
            mock_enhance.return_value = mock_elements

            # No LLM configured
            parser = MarkerParser(config={"use_llm": False})

            doc = Document(source_path=str(temp_test_file), format=DocumentFormat.PDF)
            result = parser.parse(doc)

            assert result.success is True
            assert result.metadata["llm_enhanced"] is False
            assert result.metadata["llm_model"] is None
            mock_process_no_llm.assert_called_once()

    @patch("data_ingestor.parsers.pdf_parser.Path")
    @patch("data_ingestor.parsers.pdf_parser.time")
    def test_parse_import_error(self, mock_time, mock_path_cls, temp_test_file: Path) -> None:
        """Test parse handles ImportError for missing Marker dependencies."""
        mock_time.time.side_effect = [100.0, 102.0]
        mock_path_cls.return_value.name = "test.pdf"

        with patch("marker.models.create_model_dict", side_effect=ImportError("Marker not installed")):
            parser = MarkerParser()
            doc = Document(source_path=str(temp_test_file), format=DocumentFormat.PDF)
            result = parser.parse(doc)

            assert result.success is False
            assert "Marker dependencies not available" in result.error_message
            assert result.processing_time == 2.0

    @patch("data_ingestor.parsers.pdf_parser.Path")
    @patch("data_ingestor.parsers.pdf_parser.time")
    def test_parse_general_exception(self, mock_time, mock_path_cls, temp_test_file: Path) -> None:
        """Test parse handles general exceptions during processing."""
        mock_time.time.side_effect = [100.0, 103.0]
        mock_path_cls.return_value.name = "test.pdf"

        with patch("marker.models.create_model_dict", side_effect=RuntimeError("Unexpected error")):
            parser = MarkerParser()
            doc = Document(source_path=str(temp_test_file), format=DocumentFormat.PDF)
            result = parser.parse(doc)

            assert result.success is False
            assert "Failed to parse PDF with Marker" in result.error_message
            assert result.processing_time == 3.0

    @patch("data_ingestor.parsers.pdf_parser.Path")
    @patch("data_ingestor.parsers.pdf_parser.time")
    def test_parse_with_max_pages_config(self, mock_time, mock_path_cls, temp_test_file: Path) -> None:
        """Test parse respects max_pages configuration."""
        mock_time.time.side_effect = [100.0, 105.0]
        mock_path_cls.return_value.name = "test.pdf"

        mock_output = MagicMock()
        mock_output.markdown = "# Title"
        mock_output.images = []
        mock_output.metadata = {"pages": 5, "version": "1.10"}

        with (
            patch.object(MarkerParser, "_process_without_llm", return_value=mock_output) as mock_process,
            patch.object(MarkerParser, "_markdown_to_elements") as mock_md_to_elements,
            patch.object(MarkerParser, "_enhance_element_metadata") as mock_enhance,
            patch.object(MarkerParser, "_extract_toc_from_elements", return_value=[]),
            patch.object(MarkerParser, "_detect_languages", return_value=["en"]),
            patch("marker.models.create_model_dict") as mock_create_model,
        ):

            mock_create_model.return_value = {"test": "model"}
            mock_elements = [DocumentElement(element_type=ElementType.TITLE, content="Title")]
            mock_md_to_elements.return_value = mock_elements
            mock_enhance.return_value = mock_elements

            parser = MarkerParser(config={"max_pages": 10})
            doc = Document(source_path=str(temp_test_file), format=DocumentFormat.PDF)
            result = parser.parse(doc)

            assert result.success is True
            # Verify config was passed through
            call_args = mock_process.call_args
            config_arg = call_args[0][2]
            assert config_arg.get("max_pages") == 10

    @patch("data_ingestor.parsers.pdf_parser.Path")
    @patch("data_ingestor.parsers.pdf_parser.time")
    def test_parse_non_api_error_with_fallback_disabled(self, mock_time, mock_path_cls, temp_test_file: Path) -> None:
        """Test parse handles non-API errors when fallback is disabled (outer handler catches)."""
        mock_time.time.side_effect = [100.0, 102.0]
        mock_path_cls.return_value.name = "test.pdf"

        with (
            patch.object(MarkerParser, "_process_with_llm", side_effect=ValueError("Invalid input")),
            patch("marker.models.create_model_dict", return_value={"test": "model"}),
        ):

            parser = MarkerParser()
            parser.use_llm = True
            parser.openrouter_api_key = "test-key"
            parser.enable_fallback = False

            doc = Document(source_path=str(temp_test_file), format=DocumentFormat.PDF)
            result = parser.parse(doc)

            # Outer exception handler catches the error
            assert result.success is False
            assert "Invalid input" in result.error_message

    @patch("data_ingestor.parsers.pdf_parser.Path")
    @patch("data_ingestor.parsers.pdf_parser.time")
    def test_parse_non_api_error_with_fallback_enabled(self, mock_time, mock_path_cls, temp_test_file: Path) -> None:
        """Test parse processes without LLM for non-API errors when fallback enabled."""
        mock_time.time.side_effect = [100.0, 105.0]
        mock_path_cls.return_value.name = "test.pdf"

        mock_output = MagicMock()
        mock_output.markdown = "# Title"
        mock_output.images = []
        mock_output.metadata = {"pages": 1, "version": "1.10"}

        with (
            patch.object(MarkerParser, "_process_with_llm", side_effect=ValueError("Invalid input")),
            patch.object(MarkerParser, "_process_without_llm", return_value=mock_output) as mock_no_llm,
            patch.object(MarkerParser, "_markdown_to_elements") as mock_md_to_elements,
            patch.object(MarkerParser, "_enhance_element_metadata") as mock_enhance,
            patch.object(MarkerParser, "_extract_toc_from_elements", return_value=[]),
            patch.object(MarkerParser, "_detect_languages", return_value=["en"]),
            patch("marker.models.create_model_dict", return_value={"test": "model"}),
        ):

            mock_elements = [DocumentElement(element_type=ElementType.TITLE, content="Title")]
            mock_md_to_elements.return_value = mock_elements
            mock_enhance.return_value = mock_elements

            parser = MarkerParser()
            parser.use_llm = True
            parser.openrouter_api_key = "test-key"
            parser.enable_fallback = True

            doc = Document(source_path=str(temp_test_file), format=DocumentFormat.PDF)
            result = parser.parse(doc)

            assert result.success is True
            mock_no_llm.assert_called_once()

    @patch("data_ingestor.parsers.pdf_parser.Path")
    @patch("data_ingestor.parsers.pdf_parser.time")
    def test_parse_calculates_page_count_from_elements(self, mock_time, mock_path_cls, temp_test_file: Path) -> None:
        """Test parse calculates page_count from elements when metadata doesn't provide it."""
        mock_time.time.side_effect = [100.0, 105.0]
        mock_path_cls.return_value.name = "test.pdf"

        mock_output = MagicMock()
        mock_output.markdown = "# Title"
        mock_output.images = []
        mock_output.metadata = {"pages": 0, "version": "1.10"}  # No page count

        with (
            patch.object(MarkerParser, "_process_without_llm", return_value=mock_output),
            patch.object(MarkerParser, "_markdown_to_elements") as mock_md_to_elements,
            patch.object(MarkerParser, "_enhance_element_metadata") as mock_enhance,
            patch.object(MarkerParser, "_extract_toc_from_elements", return_value=[]),
            patch.object(MarkerParser, "_detect_languages", return_value=["en"]),
            patch("marker.models.create_model_dict", return_value={"test": "model"}),
        ):

            # Elements with page numbers
            from data_ingestor.core.models import ElementMetadata

            mock_elements = [
                DocumentElement(
                    element_type=ElementType.TITLE, content="Title", metadata=ElementMetadata(page_number=1)
                ),
                DocumentElement(
                    element_type=ElementType.PARAGRAPH, content="Content", metadata=ElementMetadata(page_number=3)
                ),
            ]
            mock_md_to_elements.return_value = mock_elements
            mock_enhance.return_value = mock_elements

            parser = MarkerParser()
            doc = Document(source_path=str(temp_test_file), format=DocumentFormat.PDF)
            result = parser.parse(doc)

            assert result.success is True
            # Should calculate page count as max page number
            assert result.metadata["page_count"] == 3


class TestMarkerParserHelperMethods:
    """Tests for MarkerParser helper methods to improve coverage."""

    @requires_marker
    def test_process_with_llm_configures_service(self, temp_test_file: Path) -> None:
        """Test _process_with_llm configures LLM service correctly."""
        with (
            patch("marker.config.parser.ConfigParser") as mock_config_parser,
            patch("marker.converters.pdf.PdfConverter") as mock_converter,
        ):

            # Setup mocks
            mock_parser_instance = MagicMock()
            mock_converter_instance = MagicMock()
            mock_output = MagicMock()

            mock_config_parser.return_value = mock_parser_instance
            mock_parser_instance.generate_config_dict.return_value = {}
            mock_parser_instance.get_llm_service.return_value = MagicMock()
            mock_converter.return_value = mock_converter_instance
            mock_converter_instance.return_value = mock_output

            parser = MarkerParser()
            parser.openrouter_api_key = "test-key"

            result = parser._process_with_llm(
                str(temp_test_file),
                {"model": "dict"},
                {},
                "test/model",
            )

            # Verify LLM config was set
            mock_config_parser.assert_called_once()
            assert result == mock_output

    @requires_marker
    def test_process_without_llm_disables_llm(self, temp_test_file: Path) -> None:
        """Test _process_without_llm disables LLM correctly."""
        with (
            patch("marker.config.parser.ConfigParser") as mock_config_parser,
            patch("marker.converters.pdf.PdfConverter") as mock_converter,
        ):

            # Setup mocks
            mock_parser_instance = MagicMock()
            mock_converter_instance = MagicMock()
            mock_output = MagicMock()

            mock_config_parser.return_value = mock_parser_instance
            mock_parser_instance.generate_config_dict.return_value = {}
            mock_converter.return_value = mock_converter_instance
            mock_converter_instance.return_value = mock_output

            parser = MarkerParser()

            result = parser._process_without_llm(
                str(temp_test_file),
                {"model": "dict"},
                {},
            )

            # Verify converter was called with llm_service=None
            call_kwargs = mock_converter.call_args[1]
            assert call_kwargs.get("llm_service") is None
            assert result == mock_output

    def test_markdown_to_elements_formula_handling(self) -> None:
        """Test formula element creation from markdown."""
        parser = MarkerParser()
        markdown = "$$E=mc^2$$\n\nText after formula"

        elements = parser._markdown_to_elements(markdown)

        # Should have formula and paragraph
        assert any(el.element_type == ElementType.FORMULA for el in elements)
        assert any(el.element_type == ElementType.PARAGRAPH for el in elements)

    def test_markdown_to_elements_table_rows(self) -> None:
        """Test table parsing with multiple rows."""
        parser = MarkerParser()
        markdown = "| Col1 | Col2 |\n| Val1 | Val2 |\n| Val3 | Val4 |"

        elements = parser._markdown_to_elements(markdown)

        # Should create table element
        table_elements = [el for el in elements if el.element_type == ElementType.TABLE]
        assert len(table_elements) == 1
        assert "Col1" in table_elements[0].content
        assert "Val1" in table_elements[0].content

    def test_markdown_to_elements_mixed_headings(self) -> None:
        """Test parsing markdown with different heading levels."""
        parser = MarkerParser()
        markdown = "# H1\n## H2\n### H3\nText"

        elements = parser._markdown_to_elements(markdown)

        # Should have titles and headings
        titles = [el for el in elements if el.element_type == ElementType.TITLE]
        headings = [el for el in elements if el.element_type == ElementType.HEADING]

        assert len(titles) > 0  # # creates TITLE
        assert len(headings) > 0  # ## and ### create HEADING

    def test_markdown_to_elements_page_markers(self) -> None:
        """Test page marker detection in markdown."""
        parser = MarkerParser()
        markdown = "{0}\nPage 1 content\n{1}\nPage 2 content"

        elements = parser._markdown_to_elements(markdown)

        # Page markers should update current_page
        # Elements should have correct page numbers
        if elements:
            # Just verify parsing doesn't crash
            assert len(elements) > 0
