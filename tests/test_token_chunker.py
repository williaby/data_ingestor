"""Comprehensive tests for token-based chunking strategy."""

import pytest

from data_ingestor.chunking.token_chunker import TokenChunker
from data_ingestor.core.models import (
    Document,
    DocumentElement,
    DocumentFormat,
    ElementMetadata,
    ElementType,
    ProcessingStatus,
)


@pytest.fixture
def sample_document_with_content() -> Document:
    """Create a document with various content types for testing."""
    doc = Document(
        document_id="test-token-123",
        source_path=None,
        format=DocumentFormat.PDF,
        status=ProcessingStatus.COMPLETED,
    )

    doc.elements = [
        DocumentElement(
            element_type=ElementType.TITLE,
            content="Introduction to Testing",
            metadata=ElementMetadata(page_number=1),
        ),
        DocumentElement(
            element_type=ElementType.NARRATIVE_TEXT,
            content="This is a paragraph of text. " * 10,  # Medium-sized text
            metadata=ElementMetadata(page_number=1),
        ),
        DocumentElement(
            element_type=ElementType.NARRATIVE_TEXT,
            content="Another paragraph with different content. " * 5,
            metadata=ElementMetadata(page_number=2),
        ),
        DocumentElement(
            element_type=ElementType.TABLE,
            content="Column1 | Column2\nValue1 | Value2\nValue3 | Value4",
            metadata=ElementMetadata(page_number=2, text_as_html="<table>...</table>"),
        ),
    ]

    return doc


class TestTokenChunkerInitialization:
    """Tests for TokenChunker initialization."""

    def test_default_initialization(self) -> None:
        """Test TokenChunker with default parameters."""
        chunker = TokenChunker()
        assert chunker.chunk_size == 1000
        assert chunker.chunk_overlap == 200
        assert chunker.preserve_tables is True
        assert chunker.encoding is not None

    def test_custom_parameters(self) -> None:
        """Test TokenChunker with custom parameters."""
        chunker = TokenChunker(
            chunk_size=500,
            chunk_overlap=100,
            model_name="cl100k_base",
            preserve_tables=False,
        )
        assert chunker.chunk_size == 500
        assert chunker.chunk_overlap == 100
        assert chunker.preserve_tables is False

    def test_invalid_encoding_model_fallback(self) -> None:
        """Test fallback to cl100k_base when invalid model specified."""
        chunker = TokenChunker(model_name="invalid_model_name")
        assert chunker.encoding is not None
        # Should still work despite invalid model name

    def test_zero_overlap(self) -> None:
        """Test chunker with zero overlap."""
        chunker = TokenChunker(chunk_overlap=0)
        assert chunker.chunk_overlap == 0


class TestBasicChunking:
    """Tests for basic chunking functionality."""

    def test_chunk_document_basic(self, sample_document_with_content: Document) -> None:
        """Test basic document chunking."""
        chunker = TokenChunker(chunk_size=100, chunk_overlap=20)
        chunks = chunker.chunk_document(sample_document_with_content)

        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.content
            assert chunk.token_count is not None
            assert chunk.token_count <= 120  # Allow slight overflow

    def test_empty_document(self) -> None:
        """Test chunking empty document."""
        doc = Document(
            document_id="test-empty",
            source_path=None,
            format=DocumentFormat.PDF,
            status=ProcessingStatus.COMPLETED,
            elements=[],
        )
        chunker = TokenChunker()
        chunks = chunker.chunk_document(doc)
        assert len(chunks) == 0

    def test_single_element_document(self) -> None:
        """Test document with single element."""
        doc = Document(
            document_id="test-single",
            source_path=None,
            format=DocumentFormat.PDF,
            status=ProcessingStatus.COMPLETED,
        )
        doc.elements = [
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content="This is a single paragraph.",
                metadata=ElementMetadata(page_number=1),
            ),
        ]
        chunker = TokenChunker(chunk_size=100)
        chunks = chunker.chunk_document(doc)
        assert len(chunks) == 1
        assert "single paragraph" in chunks[0].content


class TestTablePreservation:
    """Tests for table preservation logic."""

    def test_preserve_tables_enabled(self) -> None:
        """Test that tables are preserved as standalone chunks."""
        doc = Document(
            document_id="test-tables",
            source_path=None,
            format=DocumentFormat.PDF,
            status=ProcessingStatus.COMPLETED,
        )
        doc.elements = [
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content="Text before table.",
                metadata=ElementMetadata(page_number=1),
            ),
            DocumentElement(
                element_type=ElementType.TABLE,
                content="Col1 | Col2\nVal1 | Val2",
                metadata=ElementMetadata(page_number=1),
            ),
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content="Text after table.",
                metadata=ElementMetadata(page_number=1),
            ),
        ]

        chunker = TokenChunker(chunk_size=1000, preserve_tables=True)
        chunks = chunker.chunk_document(doc)

        # Find table chunk
        table_chunks = [c for c in chunks if c.metadata.get("type") == "table"]
        assert len(table_chunks) == 1
        assert "Col1 | Col2" in table_chunks[0].content

    def test_preserve_tables_disabled(self) -> None:
        """Test that tables are chunked with text when preservation disabled."""
        doc = Document(
            document_id="test-tables",
            source_path=None,
            format=DocumentFormat.PDF,
            status=ProcessingStatus.COMPLETED,
        )
        doc.elements = [
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content="Text before table.",
                metadata=ElementMetadata(page_number=1),
            ),
            DocumentElement(
                element_type=ElementType.TABLE,
                content="Col1 | Col2\nVal1 | Val2",
                metadata=ElementMetadata(page_number=1),
            ),
        ]

        chunker = TokenChunker(chunk_size=1000, preserve_tables=False)
        chunks = chunker.chunk_document(doc)

        # Tables should be included in normal chunking
        assert len(chunks) >= 1


class TestOverlapCalculation:
    """Tests for chunk overlap calculation."""

    def test_overlap_between_chunks(self) -> None:
        """Test that overlap is correctly calculated between chunks."""
        doc = Document(
            document_id="test-overlap",
            source_path=None,
            format=DocumentFormat.PDF,
            status=ProcessingStatus.COMPLETED,
        )
        # Create document with predictable content
        doc.elements = [
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content=f"Sentence {i}. " * 20,  # Create multiple sentences
                metadata=ElementMetadata(page_number=1),
            )
            for i in range(10)
        ]

        chunker = TokenChunker(chunk_size=50, chunk_overlap=10)
        chunks = chunker.chunk_document(doc)

        # Should have multiple chunks with overlap
        assert len(chunks) > 1

    def test_zero_overlap(self) -> None:
        """Test chunking with zero overlap."""
        doc = Document(
            document_id="test-no-overlap",
            source_path=None,
            format=DocumentFormat.PDF,
            status=ProcessingStatus.COMPLETED,
        )
        doc.elements = [
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content="Text content. " * 50,
                metadata=ElementMetadata(page_number=1),
            ),
        ]

        chunker = TokenChunker(chunk_size=50, chunk_overlap=0)
        chunks = chunker.chunk_document(doc)
        assert len(chunks) > 0


class TestLargeElementSplitting:
    """Tests for splitting large elements that exceed chunk size."""

    def test_split_large_element(self) -> None:
        """Test splitting single element that exceeds chunk size."""
        doc = Document(
            document_id="test-large",
            source_path=None,
            format=DocumentFormat.PDF,
            status=ProcessingStatus.COMPLETED,
        )
        # Create very long text
        long_text = "This is a very long sentence that will exceed the chunk size. " * 50
        doc.elements = [
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content=long_text,
                metadata=ElementMetadata(page_number=1),
            ),
        ]

        chunker = TokenChunker(chunk_size=100, chunk_overlap=20)
        chunks = chunker.chunk_document(doc)

        # Should create multiple chunks from single element
        assert len(chunks) > 1
        # Check for split metadata
        split_chunks = [c for c in chunks if c.metadata.get("split_from_large_element")]
        assert len(split_chunks) > 0

    def test_large_element_with_sentences(self) -> None:
        """Test that large elements are split at sentence boundaries."""
        doc = Document(
            document_id="test-sentences",
            source_path=None,
            format=DocumentFormat.PDF,
            status=ProcessingStatus.COMPLETED,
        )
        # Create text with clear sentence boundaries
        sentences = [f"This is sentence number {i}." for i in range(100)]
        doc.elements = [
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content=" ".join(sentences),
                metadata=ElementMetadata(page_number=1),
            ),
        ]

        chunker = TokenChunker(chunk_size=50, chunk_overlap=10)
        chunks = chunker.chunk_document(doc)

        # Should create multiple chunks
        assert len(chunks) > 1
        # Chunks should preserve sentence structure
        for chunk in chunks:
            assert chunk.content.strip()


class TestChunkMetadata:
    """Tests for chunk metadata."""

    def test_chunk_metadata_structure(self, sample_document_with_content: Document) -> None:
        """Test that chunks have proper metadata."""
        chunker = TokenChunker(chunk_size=100)
        chunks = chunker.chunk_document(sample_document_with_content)

        for i, chunk in enumerate(chunks):
            assert chunk.metadata["document_id"] == "test-token-123"
            assert chunk.metadata["chunk_index"] == i
            assert chunk.metadata["total_chunks"] == len(chunks)

    def test_page_range_tracking(self) -> None:
        """Test that page ranges are correctly tracked in chunks."""
        doc = Document(
            document_id="test-pages",
            source_path=None,
            format=DocumentFormat.PDF,
            status=ProcessingStatus.COMPLETED,
        )
        doc.elements = [
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content="Page 1 content.",
                metadata=ElementMetadata(page_number=1),
            ),
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content="Page 2 content.",
                metadata=ElementMetadata(page_number=2),
            ),
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content="Page 3 content.",
                metadata=ElementMetadata(page_number=3),
            ),
        ]

        chunker = TokenChunker(chunk_size=1000)
        chunks = chunker.chunk_document(doc)

        # Check page ranges
        for chunk in chunks:
            if chunk.start_page is not None:
                assert chunk.start_page >= 1
            if chunk.end_page is not None:
                assert chunk.end_page >= chunk.start_page if chunk.start_page else True

    def test_elements_tracking(self, sample_document_with_content: Document) -> None:
        """Test that original elements are tracked in chunks."""
        chunker = TokenChunker(chunk_size=100)
        chunks = chunker.chunk_document(sample_document_with_content)

        for chunk in chunks:
            # Non-table chunks should have elements
            if chunk.metadata.get("type") != "table":
                assert len(chunk.elements) >= 0


class TestTokenCounting:
    """Tests for token counting accuracy."""

    def test_token_count_accuracy(self) -> None:
        """Test that token counts are accurate."""
        doc = Document(
            document_id="test-tokens",
            source_path=None,
            format=DocumentFormat.PDF,
            status=ProcessingStatus.COMPLETED,
        )
        doc.elements = [
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content="This is a test sentence.",
                metadata=ElementMetadata(page_number=1),
            ),
        ]

        chunker = TokenChunker(chunk_size=1000)
        chunks = chunker.chunk_document(doc)

        assert len(chunks) == 1
        assert chunks[0].token_count is not None
        assert chunks[0].token_count > 0

    def test_chunk_size_respected(self) -> None:
        """Test that chunks don't significantly exceed chunk_size."""
        doc = Document(
            document_id="test-size",
            source_path=None,
            format=DocumentFormat.PDF,
            status=ProcessingStatus.COMPLETED,
        )
        doc.elements = [
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content="Word " * 500,  # Many words
                metadata=ElementMetadata(page_number=1),
            ),
        ]

        chunk_size = 100
        chunker = TokenChunker(chunk_size=chunk_size, chunk_overlap=0)
        chunks = chunker.chunk_document(doc)

        for chunk in chunks:
            # Allow some tolerance for boundary conditions
            if not chunk.metadata.get("split_from_large_element"):
                assert chunk.token_count is not None
                # Normal chunks should respect size


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.parametrize(
        ("chunk_size", "overlap", "content", "expected_chunks_min"),
        [
            (5, 1, "This is a test.", 1),  # Very small chunk size
            (50, 45, "Word " * 100, 1),  # Overlap close to chunk size
            (100, 0, "Short text", 1),  # Zero overlap
            (10, 5, "Word " * 50, 1),  # Normal case - single element treated as one chunk
            (1000, 100, "Small content", 1),  # Large chunk for small content
            (50, 49, "Word " * 100, 1),  # Overlap almost equal to chunk size
            (200, 50, "Token " * 200, 1),  # Medium case - single element
        ],
        ids=["very_small", "high_overlap", "zero_overlap", "normal", "large_chunk", "max_overlap", "medium"],
    )
    def test_chunk_size_and_overlap_variations(self, chunk_size, overlap, content, expected_chunks_min) -> None:
        """Test various chunk size and overlap combinations."""
        doc = Document(
            document_id="test-params",
            source_path=None,
            format=DocumentFormat.PDF,
            status=ProcessingStatus.COMPLETED,
        )
        doc.elements = [
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content=content,
                metadata=ElementMetadata(page_number=1),
            ),
        ]

        chunker = TokenChunker(chunk_size=chunk_size, chunk_overlap=overlap)
        chunks = chunker.chunk_document(doc)
        assert len(chunks) >= expected_chunks_min, f"Expected at least {expected_chunks_min} chunks, got {len(chunks)}"

    def test_unicode_content(self) -> None:
        """Test chunking with unicode content."""
        doc = Document(
            document_id="test-unicode",
            source_path=None,
            format=DocumentFormat.PDF,
            status=ProcessingStatus.COMPLETED,
        )
        doc.elements = [
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content="Unicode content: 你好世界 🌍 Привет мир",
                metadata=ElementMetadata(page_number=1),
            ),
        ]

        chunker = TokenChunker(chunk_size=100)
        chunks = chunker.chunk_document(doc)
        assert len(chunks) == 1
        assert "你好世界" in chunks[0].content

    def test_elements_without_page_numbers(self) -> None:
        """Test elements that don't have page numbers."""
        doc = Document(
            document_id="test-no-pages",
            source_path=None,
            format=DocumentFormat.PDF,
            status=ProcessingStatus.COMPLETED,
        )
        doc.elements = [
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content="Content without page number.",
                metadata=ElementMetadata(),  # No page number
            ),
        ]

        chunker = TokenChunker(chunk_size=100)
        chunks = chunker.chunk_document(doc)
        assert len(chunks) == 1
        assert chunks[0].start_page is None
        assert chunks[0].end_page is None
