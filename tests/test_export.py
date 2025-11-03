"""Tests for document export functionality."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from data_ingestor.core.models import (
    Document,
    DocumentElement,
    DocumentFormat,
    ElementMetadata,
    ElementType,
    ProcessingStatus,
)
from data_ingestor.export.exporter import DocumentExporter, OutputFormat


@pytest.fixture
def sample_document() -> Document:
    """Create a sample document for testing."""
    doc = Document(
        document_id="test-123",
        source_path="/path/to/test.pdf",
        format=DocumentFormat.PDF,
        status=ProcessingStatus.COMPLETED,
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 30, tzinfo=UTC),
        metadata={
            "title": "Test Document",
            "author": "Test Author",
            "pages": 5,
        },
        parser_used="PyMuPDFParser",
        processing_time=2.5,
    )

    # Add sample elements
    doc.elements = [
        DocumentElement(
            element_type=ElementType.TITLE,
            content="Introduction",
            metadata=ElementMetadata(
                page_number=1,
                category_depth=1,
            ),
        ),
        DocumentElement(
            element_type=ElementType.NARRATIVE_TEXT,
            content="This is the first paragraph of text.",
            metadata=ElementMetadata(
                page_number=1,
            ),
        ),
        DocumentElement(
            element_type=ElementType.TABLE,
            content="Column1 | Column2\nValue1 | Value2",
            metadata=ElementMetadata(
                page_number=2,
                text_as_html="<table><tr><td>Column1</td><td>Column2</td></tr></table>",
            ),
        ),
    ]

    return doc


class TestDocumentExporter:
    """Tests for DocumentExporter class."""

    def test_json_export(self, sample_document: Document, tmp_path: Path) -> None:
        """Test JSON export functionality."""
        exporter = DocumentExporter()
        json_data = exporter.to_json(sample_document)

        # Verify structure
        assert json_data["document_id"] == "test-123"
        assert json_data["source_path"] == "/path/to/test.pdf"
        assert json_data["format"] == "pdf"
        assert json_data["status"] == "completed"
        assert json_data["parser_used"] == "PyMuPDFParser"
        assert json_data["processing_time"] == 2.5

        # Verify metadata
        assert json_data["metadata"]["title"] == "Test Document"
        assert json_data["metadata"]["pages"] == 5

        # Verify elements
        assert len(json_data["elements"]) == 3
        assert json_data["elements"][0]["type"] == "title"
        assert json_data["elements"][0]["content"] == "Introduction"

        # Test file writing
        output_path = tmp_path / "test.json"
        exporter.export(sample_document, OutputFormat.JSON, output_path)
        assert output_path.exists()

        # Verify file content
        with output_path.open() as f:
            loaded_data = json.load(f)
        assert loaded_data["document_id"] == "test-123"

    def test_markdown_export(self, sample_document: Document) -> None:
        """Test Markdown export functionality."""
        exporter = DocumentExporter()
        markdown = exporter.to_markdown(sample_document)

        # Verify YAML front matter
        assert "---" in markdown
        assert "document_id: test-123" in markdown
        assert "format: pdf" in markdown

        # Verify content structure
        assert "# Introduction" in markdown
        assert "This is the first paragraph of text." in markdown
        assert "Column1 | Column2" in markdown

    def test_markdown_with_yaml_parsing(self, sample_document: Document) -> None:
        """Test that markdown YAML front matter is valid."""
        exporter = DocumentExporter()
        markdown = exporter.to_markdown(sample_document)

        # Extract front matter
        parts = markdown.split("---")
        assert len(parts) >= 3
        front_matter = parts[1].strip()

        # Parse YAML
        data = yaml.safe_load(front_matter)
        assert data["document_id"] == "test-123"
        assert data["format"] == "pdf"
        assert data["total_elements"] == 3

    def test_dual_export(self, sample_document: Document, tmp_path: Path) -> None:
        """Test dual format export (JSON + Markdown)."""
        exporter = DocumentExporter()
        base_path = tmp_path / "document"

        result = exporter.export(sample_document, OutputFormat.BOTH, base_path)

        # Verify return value
        assert isinstance(result, tuple)
        json_data, markdown_data = result
        assert isinstance(json_data, dict)
        assert isinstance(markdown_data, str)

        # Verify files created
        json_path = base_path.with_suffix(".json")
        md_path = base_path.with_suffix(".md")
        assert json_path.exists()
        assert md_path.exists()

    def test_text_export(self, sample_document: Document) -> None:
        """Test plain text export."""
        exporter = DocumentExporter()
        text = exporter.to_text(sample_document)

        # Verify content
        assert "Introduction" in text
        assert "This is the first paragraph of text." in text
        assert "Column1 | Column2" in text

    def test_markdown_with_chunks(self, sample_document: Document) -> None:
        """Test markdown export with chunks included."""
        from data_ingestor.core.models import Chunk

        # Add chunks to document
        sample_document.chunks = [
            Chunk(
                content="Introduction\n\nThis is the first paragraph of text.",
                token_count=50,
                start_page=1,
                end_page=1,
            ),
        ]

        exporter = DocumentExporter()
        markdown = exporter.to_markdown(sample_document, include_chunks=True)

        # Verify chunk section exists
        assert "## Document Chunks" in markdown
        assert "### Chunk 1" in markdown
        assert "**Tokens**: 50" in markdown

    def test_element_to_markdown_formatting(self) -> None:
        """Test element-to-markdown conversion preserves formatting."""
        exporter = DocumentExporter()

        # Test heading
        heading = DocumentElement(
            element_type=ElementType.HEADING,
            content="Section Title",
            metadata=ElementMetadata(category_depth=2),
        )
        result = exporter._element_to_markdown(heading)
        assert result == "## Section Title\n"

        # Test list item
        list_item = DocumentElement(
            element_type=ElementType.LIST_ITEM,
            content="List item text",
        )
        result = exporter._element_to_markdown(list_item)
        assert result == "- List item text\n"

        # Test code snippet
        code = DocumentElement(
            element_type=ElementType.CODE_SNIPPET,
            content="print('hello')",
        )
        result = exporter._element_to_markdown(code)
        assert "```" in result
        assert "print('hello')" in result

        # Test formula
        formula = DocumentElement(
            element_type=ElementType.FORMULA,
            content="E = mc^2",
        )
        result = exporter._element_to_markdown(formula)
        assert "$$E = mc^2$$" in result

    def test_unsupported_format_raises_error(self, sample_document: Document) -> None:
        """Test that unsupported format raises ValueError."""
        exporter = DocumentExporter()

        with pytest.raises(ValueError, match="Unsupported format"):
            # Create a mock format that doesn't exist
            exporter.export(sample_document, "invalid_format", None)  # type: ignore

    def test_metadata_preservation(self, sample_document: Document) -> None:
        """Test that metadata is preserved in export."""
        exporter = DocumentExporter()
        json_data = exporter.to_json(sample_document)

        # Verify element metadata
        element_meta = json_data["elements"][0]["metadata"]
        assert element_meta["page_number"] == 1
        assert element_meta["category_depth"] == 1

        # Verify table metadata
        table_meta = json_data["elements"][2]["metadata"]
        assert table_meta["text_as_html"] is not None
        assert "<table>" in table_meta["text_as_html"]
