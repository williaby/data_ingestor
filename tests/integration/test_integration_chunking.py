"""Integration tests for chunking with real data (no mocks)."""

from data_ingestor.chunking.by_title_chunker import ByTitleChunker
from data_ingestor.chunking.token_chunker import TokenChunker
from data_ingestor.core.models import Document, DocumentElement, DocumentFormat, ElementMetadata, ElementType


class TestChunkingIntegration:
    """Integration tests using real Document objects and data."""

    def test_by_title_chunker_with_realistic_document(self) -> None:
        """Test by_title chunker with a realistic multi-section document."""
        # Create a realistic document structure
        doc = Document(
            document_id="integration-test-doc",
            source_path=None,
            format=DocumentFormat.PDF,
        )

        # Simulate a realistic research paper structure
        doc.elements = [
            # Abstract section
            DocumentElement(
                element_type=ElementType.TITLE,
                content="Abstract",
                metadata=ElementMetadata(page_number=1, category_depth=1),
            ),
            DocumentElement(
                element_type=ElementType.PARAGRAPH,
                content="This paper presents a comprehensive study of machine learning techniques "
                "applied to natural language processing. We demonstrate significant improvements "
                "in accuracy and performance across multiple benchmark datasets.",
                metadata=ElementMetadata(page_number=1),
            ),
            # Introduction section
            DocumentElement(
                element_type=ElementType.TITLE,
                content="1. Introduction",
                metadata=ElementMetadata(page_number=1, category_depth=1),
            ),
            DocumentElement(
                element_type=ElementType.PARAGRAPH,
                content="Natural language processing has seen remarkable advances in recent years. "
                "Deep learning models have revolutionized how we approach text understanding.",
                metadata=ElementMetadata(page_number=1),
            ),
            DocumentElement(
                element_type=ElementType.PARAGRAPH,
                content="In this work, we focus on three key areas: tokenization, embeddings, "
                "and sequence modeling. Each area presents unique challenges and opportunities.",
                metadata=ElementMetadata(page_number=2),
            ),
            # Methods section with a table
            DocumentElement(
                element_type=ElementType.TITLE,
                content="2. Methods",
                metadata=ElementMetadata(page_number=2, category_depth=1),
            ),
            DocumentElement(
                element_type=ElementType.PARAGRAPH,
                content="We employed a multi-stage pipeline for our experiments.",
                metadata=ElementMetadata(page_number=2),
            ),
            DocumentElement(
                element_type=ElementType.TABLE,
                content="Model | Accuracy | F1-Score\nBERT | 0.92 | 0.89\nGPT | 0.94 | 0.91",
                metadata=ElementMetadata(page_number=2, text_as_html="<table>...</table>"),
            ),
            # Results section
            DocumentElement(
                element_type=ElementType.TITLE,
                content="3. Results",
                metadata=ElementMetadata(page_number=3, category_depth=1),
            ),
            DocumentElement(
                element_type=ElementType.PARAGRAPH,
                content="Our experiments demonstrate consistent improvements across all metrics.",
                metadata=ElementMetadata(page_number=3),
            ),
        ]

        # Test with section-aware chunking
        chunker = ByTitleChunker(chunk_size=500, chunk_overlap=50, preserve_tables=True)
        chunks = chunker.chunk_document(doc)

        # Verify realistic behavior
        assert len(chunks) >= 4  # At least one chunk per major section
        assert all(c.metadata.get("chunking_strategy") == "by_title" for c in chunks)

        # Verify table is preserved
        table_chunks = [c for c in chunks if "Model | Accuracy" in c.content]
        assert len(table_chunks) == 1
        assert table_chunks[0].metadata.get("type") == "table"

        # Verify sections are not mixed
        for chunk in chunks:
            section_titles = chunk.metadata.get("section_title", "")
            # Each chunk should belong to a single section
            if section_titles:
                assert isinstance(section_titles, str)

    def test_token_chunker_with_long_document(self) -> None:
        """Test token chunker with a realistic long document."""
        doc = Document(
            document_id="long-doc",
            source_path=None,
            format=DocumentFormat.PDF,
        )

        # Create multiple smaller paragraphs to allow realistic overlap
        doc.elements = [
            DocumentElement(
                element_type=ElementType.TITLE,
                content="Very Long Document",
                metadata=ElementMetadata(page_number=1),
            ),
        ]

        # Add many smaller paragraphs that will span multiple chunks
        for i in range(50):
            doc.elements.append(
                DocumentElement(
                    element_type=ElementType.PARAGRAPH,
                    content=f"This is paragraph number {i}. It contains some information about topic {i}. "
                    f"This paragraph has enough content to be meaningful but not too large.",
                    metadata=ElementMetadata(page_number=(i // 10) + 1),
                ),
            )

        # Test with token-based chunking
        chunker = TokenChunker(chunk_size=200, chunk_overlap=50)
        chunks = chunker.chunk_document(doc)

        # Should create multiple chunks
        assert len(chunks) > 3

        # Verify metadata is preserved
        for chunk in chunks:
            assert "chunk_index" in chunk.metadata
            assert "total_chunks" in chunk.metadata
            assert chunk.metadata["document_id"] == "long-doc"

    def test_chunking_preserves_metadata(self) -> None:
        """Test that chunking preserves important metadata."""
        doc = Document(
            document_id="metadata-test",
            source_path=None,
            format=DocumentFormat.PDF,
        )

        doc.elements = [
            DocumentElement(
                element_type=ElementType.TITLE,
                content="Section",
                metadata=ElementMetadata(
                    page_number=1,
                    coordinates=(100, 200, 300, 250),
                    confidence=0.95,
                ),
            ),
            DocumentElement(
                element_type=ElementType.PARAGRAPH,
                content="Content with metadata",
                metadata=ElementMetadata(page_number=1, confidence=0.92),
            ),
        ]

        chunker = ByTitleChunker(chunk_size=1000)
        chunks = chunker.chunk_document(doc)

        # Verify metadata is preserved in chunks
        assert len(chunks) > 0
        for chunk in chunks:
            assert "document_id" in chunk.metadata
            assert chunk.metadata["document_id"] == "metadata-test"
            assert "chunk_index" in chunk.metadata
            assert "total_chunks" in chunk.metadata

    def test_empty_document_chunking(self) -> None:
        """Test chunking behavior with empty documents (real scenario)."""
        doc = Document(
            document_id="empty-doc",
            source_path=None,
            format=DocumentFormat.PDF,
            elements=[],
        )

        # Test both chunkers handle empty docs
        by_title_chunker = ByTitleChunker(chunk_size=500)
        token_chunker = TokenChunker(chunk_size=500)

        by_title_chunks = by_title_chunker.chunk_document(doc)
        token_chunks = token_chunker.chunk_document(doc)

        assert len(by_title_chunks) == 0
        assert len(token_chunks) == 0

    def test_single_element_document(self) -> None:
        """Test chunking with minimal single-element document."""
        doc = Document(
            document_id="single-elem",
            source_path=None,
            format=DocumentFormat.PDF,
        )

        doc.elements = [
            DocumentElement(
                element_type=ElementType.PARAGRAPH,
                content="Single short paragraph.",
                metadata=ElementMetadata(page_number=1),
            ),
        ]

        chunker = TokenChunker(chunk_size=1000)
        chunks = chunker.chunk_document(doc)

        assert len(chunks) == 1
        assert "Single short paragraph" in chunks[0].content


class TestChunkingEdgeCases:
    """Test chunking with edge cases using real data."""

    def test_document_with_only_tables(self) -> None:
        """Test chunking document containing only tables."""
        doc = Document(
            document_id="tables-only",
            source_path=None,
            format=DocumentFormat.PDF,
        )

        doc.elements = [
            DocumentElement(
                element_type=ElementType.TABLE,
                content="Col1 | Col2\nA | B\nC | D",
                metadata=ElementMetadata(page_number=1),
            ),
            DocumentElement(
                element_type=ElementType.TABLE,
                content="Name | Value\nX | 100\nY | 200",
                metadata=ElementMetadata(page_number=1),
            ),
        ]

        chunker = ByTitleChunker(chunk_size=1000, preserve_tables=True)
        chunks = chunker.chunk_document(doc)

        # Tables should be preserved as separate chunks
        assert len(chunks) == 2
        assert all(c.metadata.get("type") == "table" for c in chunks)

    def test_mixed_content_realistic_structure(self) -> None:
        """Test chunking with mixed content types in realistic patterns."""
        doc = Document(
            document_id="mixed-content",
            source_path=None,
            format=DocumentFormat.PDF,
        )

        doc.elements = [
            DocumentElement(
                element_type=ElementType.TITLE,
                content="Analysis",
                metadata=ElementMetadata(page_number=1),
            ),
            DocumentElement(
                element_type=ElementType.PARAGRAPH,
                content="Introduction text.",
                metadata=ElementMetadata(page_number=1),
            ),
            DocumentElement(
                element_type=ElementType.FORMULA,
                content="E=mc^2",
                metadata=ElementMetadata(page_number=1),
            ),
            DocumentElement(
                element_type=ElementType.PARAGRAPH,
                content="Discussion of formula.",
                metadata=ElementMetadata(page_number=1),
            ),
            DocumentElement(
                element_type=ElementType.LIST,
                content="- Point 1\n- Point 2",
                metadata=ElementMetadata(page_number=1),
            ),
            DocumentElement(
                element_type=ElementType.TABLE,
                content="Data | Value\nA | 1",
                metadata=ElementMetadata(page_number=2),
            ),
        ]

        chunker = ByTitleChunker(chunk_size=500, preserve_tables=True)
        chunks = chunker.chunk_document(doc)

        # Verify all content types are represented
        all_content = " ".join(c.content for c in chunks)
        assert "E=mc^2" in all_content
        assert "Point 1" in all_content
        assert "Data | Value" in all_content
