"""Tests for section-aware (by_title) chunking strategy."""

from datetime import UTC, datetime

import pytest

from data_ingestor.chunking.by_title_chunker import ByTitleChunker, ChunkingStrategy
from data_ingestor.core.models import (
    Document,
    DocumentElement,
    DocumentFormat,
    ElementMetadata,
    ElementType,
    ProcessingStatus,
)


@pytest.fixture
def sample_document_with_sections() -> Document:
    """Create a document with multiple sections for testing."""
    doc = Document(
        document_id="test-sections-123",
        source_path="/path/to/test.pdf",
        format=DocumentFormat.PDF,
        status=ProcessingStatus.COMPLETED,
    )

    # Add elements with multiple sections
    doc.elements = [
        # Section 1
        DocumentElement(
            element_type=ElementType.TITLE,
            content="Introduction",
            metadata=ElementMetadata(page_number=1, category_depth=1),
        ),
        DocumentElement(
            element_type=ElementType.NARRATIVE_TEXT,
            content="This is the introduction text.",
            metadata=ElementMetadata(page_number=1),
        ),
        DocumentElement(
            element_type=ElementType.NARRATIVE_TEXT,
            content="More introduction content.",
            metadata=ElementMetadata(page_number=1),
        ),
        # Section 2
        DocumentElement(
            element_type=ElementType.TITLE,
            content="Methods",
            metadata=ElementMetadata(page_number=2, category_depth=1),
        ),
        DocumentElement(
            element_type=ElementType.NARRATIVE_TEXT,
            content="Description of methods used.",
            metadata=ElementMetadata(page_number=2),
        ),
        # Section 3
        DocumentElement(
            element_type=ElementType.TITLE,
            content="Results",
            metadata=ElementMetadata(page_number=3, category_depth=1),
        ),
        DocumentElement(
            element_type=ElementType.NARRATIVE_TEXT,
            content="Our findings show significant results.",
            metadata=ElementMetadata(page_number=3),
        ),
    ]

    return doc


class TestByTitleChunker:
    """Tests for ByTitleChunker class."""

    def test_basic_section_chunking(self, sample_document_with_sections: Document) -> None:
        """Test that sections are preserved in chunking."""
        chunker = ByTitleChunker(chunk_size=1000, chunk_overlap=0)
        chunks = chunker.chunk_document(sample_document_with_sections)

        # Should have 3 chunks (one per section)
        assert len(chunks) >= 3

        # Verify section titles are tracked
        section_titles = [
            chunk.metadata.get("section_title") for chunk in chunks if chunk.metadata.get("section_title")
        ]
        assert "Introduction" in section_titles
        assert "Methods" in section_titles
        assert "Results" in section_titles

    def test_no_cross_section_chunking(self, sample_document_with_sections: Document) -> None:
        """Test that chunks never span across section boundaries."""
        chunker = ByTitleChunker(chunk_size=1000, chunk_overlap=0)
        chunks = chunker.chunk_document(sample_document_with_sections)

        # Verify no chunk contains elements from different sections
        for chunk in chunks:
            section_titles_in_chunk = [
                elem.content
                for elem in chunk.elements
                if elem.element_type in (ElementType.TITLE, ElementType.HEADING)
            ]
            # Each chunk should have at most one section title
            assert len(section_titles_in_chunk) <= 1

    def test_combine_small_sections(self) -> None:
        """Test combining small sections below threshold."""
        doc = Document(
            document_id="test-small-sections",
            source_path="/path/to/test.pdf",
            format=DocumentFormat.PDF,
            status=ProcessingStatus.COMPLETED,
        )

        # Create multiple small sections
        doc.elements = [
            DocumentElement(
                element_type=ElementType.TITLE,
                content="A",
                metadata=ElementMetadata(page_number=1),
            ),
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content="Short text.",
                metadata=ElementMetadata(page_number=1),
            ),
            DocumentElement(
                element_type=ElementType.TITLE,
                content="B",
                metadata=ElementMetadata(page_number=1),
            ),
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content="More short text.",
                metadata=ElementMetadata(page_number=1),
            ),
        ]

        # Without combine_text_under_n_chars, should have 2 chunks
        chunker = ByTitleChunker(chunk_size=1000, combine_text_under_n_chars=None)
        chunks = chunker.chunk_document(doc)
        assert len(chunks) == 2

        # With combine_text_under_n_chars=100, should combine into 1 chunk
        chunker_combine = ByTitleChunker(chunk_size=1000, combine_text_under_n_chars=100)
        chunks_combined = chunker_combine.chunk_document(doc)
        assert len(chunks_combined) == 1

    def test_table_preservation(self) -> None:
        """Test that tables are preserved as standalone chunks."""
        doc = Document(
            document_id="test-tables",
            source_path="/path/to/test.pdf",
            format=DocumentFormat.PDF,
            status=ProcessingStatus.COMPLETED,
        )

        doc.elements = [
            DocumentElement(
                element_type=ElementType.TITLE,
                content="Data Section",
                metadata=ElementMetadata(page_number=1),
            ),
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content="Here is our data:",
                metadata=ElementMetadata(page_number=1),
            ),
            DocumentElement(
                element_type=ElementType.TABLE,
                content="Col1 | Col2\nVal1 | Val2",
                metadata=ElementMetadata(
                    page_number=1,
                    text_as_html="<table>...</table>",
                ),
            ),
        ]

        chunker = ByTitleChunker(chunk_size=1000, preserve_tables=True)
        chunks = chunker.chunk_document(doc)

        # Should have at least 2 chunks: one for text, one for table
        assert len(chunks) >= 2

        # Find the table chunk
        table_chunks = [c for c in chunks if c.metadata.get("type") == "table"]
        assert len(table_chunks) == 1
        assert "Col1 | Col2" in table_chunks[0].content

    def test_page_boundary_respect(self) -> None:
        """Test that page boundaries are respected when configured."""
        doc = Document(
            document_id="test-pages",
            source_path="/path/to/test.pdf",
            format=DocumentFormat.PDF,
            status=ProcessingStatus.COMPLETED,
        )

        doc.elements = [
            DocumentElement(
                element_type=ElementType.TITLE,
                content="Section",
                metadata=ElementMetadata(page_number=1),
            ),
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content="Text on page 1.",
                metadata=ElementMetadata(page_number=1),
            ),
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content="Text on page 2.",
                metadata=ElementMetadata(page_number=2),
            ),
        ]

        # With page boundary respect, should create separate chunks
        chunker = ByTitleChunker(chunk_size=1000, respect_page_boundaries=True)
        chunks = chunker.chunk_document(doc)

        # Should have at least 2 chunks due to page boundary
        assert len(chunks) >= 2

    def test_chunk_metadata(self, sample_document_with_sections: Document) -> None:
        """Test that chunks have proper metadata."""
        chunker = ByTitleChunker(chunk_size=1000)
        chunks = chunker.chunk_document(sample_document_with_sections)

        for i, chunk in enumerate(chunks):
            # Verify standard metadata
            assert chunk.metadata["document_id"] == "test-sections-123"
            assert chunk.metadata["chunk_index"] == i
            assert chunk.metadata["total_chunks"] == len(chunks)
            assert chunk.metadata["chunking_strategy"] == "by_title"

            # Verify orig_elements tracking
            if "orig_elements" in chunk.metadata:
                assert isinstance(chunk.metadata["orig_elements"], list)
                assert len(chunk.metadata["orig_elements"]) > 0

    def test_empty_document(self) -> None:
        """Test handling of empty document."""
        doc = Document(
            document_id="test-empty",
            source_path="/path/to/test.pdf",
            format=DocumentFormat.PDF,
            status=ProcessingStatus.COMPLETED,
            elements=[],
        )

        chunker = ByTitleChunker(chunk_size=1000)
        chunks = chunker.chunk_document(doc)

        assert len(chunks) == 0

    def test_oversized_element_handling(self) -> None:
        """Test handling of single element exceeding chunk size."""
        doc = Document(
            document_id="test-oversized",
            source_path="/path/to/test.pdf",
            format=DocumentFormat.PDF,
            status=ProcessingStatus.COMPLETED,
        )

        # Create a very long element
        long_text = "This is a very long text. " * 200
        doc.elements = [
            DocumentElement(
                element_type=ElementType.TITLE,
                content="Section",
                metadata=ElementMetadata(page_number=1),
            ),
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content=long_text,
                metadata=ElementMetadata(page_number=1),
            ),
        ]

        chunker = ByTitleChunker(chunk_size=100)  # Small chunk size
        chunks = chunker.chunk_document(doc)

        # Should have at least one chunk marked as oversized
        oversized_chunks = [c for c in chunks if c.metadata.get("oversized_element")]
        assert len(oversized_chunks) > 0

    def test_chunking_strategy_enum(self) -> None:
        """Test ChunkingStrategy enum."""
        assert ChunkingStrategy.BASIC == "basic"
        assert ChunkingStrategy.BY_TITLE == "by_title"
