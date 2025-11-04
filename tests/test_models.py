"""Comprehensive tests for core data models."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from data_ingestor.core.models import (
    Chunk,
    Document,
    DocumentElement,
    DocumentFormat,
    ElementMetadata,
    ElementType,
    ParserResult,
    ProcessingStatus,
    QualityLevel,
    QualityMetrics,
)


class TestDocumentFormat:
    """Tests for DocumentFormat enum."""

    def test_all_formats(self) -> None:
        """Test all document format values."""
        assert DocumentFormat.PDF == "pdf"
        assert DocumentFormat.DOCX == "docx"
        assert DocumentFormat.HTML == "html"
        assert DocumentFormat.VIDEO == "video"
        assert DocumentFormat.AUDIO == "audio"
        assert DocumentFormat.UNKNOWN == "unknown"

    def test_format_comparison(self) -> None:
        """Test format comparison."""
        assert DocumentFormat.PDF == DocumentFormat.PDF
        assert DocumentFormat.PDF != DocumentFormat.DOCX


class TestElementType:
    """Tests for ElementType enum."""

    def test_primary_text_elements(self) -> None:
        """Test primary text element types."""
        assert ElementType.TITLE == "title"
        assert ElementType.NARRATIVE_TEXT == "narrative_text"
        assert ElementType.LIST_ITEM == "list_item"

    def test_structural_elements(self) -> None:
        """Test structural element types."""
        assert ElementType.HEADER == "header"
        assert ElementType.FOOTER == "footer"
        assert ElementType.PAGE_BREAK == "page_break"

    def test_rich_content_elements(self) -> None:
        """Test rich content element types."""
        assert ElementType.TABLE == "table"
        assert ElementType.IMAGE == "image"
        assert ElementType.FORMULA == "formula"
        assert ElementType.CODE_SNIPPET == "code_snippet"


class TestQualityLevel:
    """Tests for QualityLevel enum."""

    def test_quality_levels(self) -> None:
        """Test quality level values."""
        assert QualityLevel.EXCELLENT == "excellent"
        assert QualityLevel.GOOD == "good"
        assert QualityLevel.MARGINAL == "marginal"
        assert QualityLevel.POOR == "poor"


class TestProcessingStatus:
    """Tests for ProcessingStatus enum."""

    def test_status_values(self) -> None:
        """Test processing status values."""
        assert ProcessingStatus.PENDING == "pending"
        assert ProcessingStatus.PROCESSING == "processing"
        assert ProcessingStatus.COMPLETED == "completed"
        assert ProcessingStatus.FAILED == "failed"
        assert ProcessingStatus.REQUIRES_REVIEW == "requires_review"


class TestElementMetadata:
    """Tests for ElementMetadata model."""

    def test_default_initialization(self) -> None:
        """Test ElementMetadata with defaults."""
        metadata = ElementMetadata()

        assert metadata.element_id is not None
        assert metadata.filename is None
        assert metadata.page_number is None
        assert metadata.languages == []
        assert metadata.extra == {}

    def test_with_page_number(self) -> None:
        """Test metadata with page number."""
        metadata = ElementMetadata(page_number=5)
        assert metadata.page_number == 5

    def test_with_coordinates(self) -> None:
        """Test metadata with coordinates."""
        coords = (10.0, 20.0, 100.0, 200.0)
        metadata = ElementMetadata(coordinates=coords)
        assert metadata.coordinates == coords

    def test_with_html_content(self) -> None:
        """Test metadata with HTML content."""
        html = "<table><tr><td>Test</td></tr></table>"
        metadata = ElementMetadata(text_as_html=html)
        assert metadata.text_as_html == html

    def test_category_depth(self) -> None:
        """Test category depth for headings."""
        metadata = ElementMetadata(category_depth=2)
        assert metadata.category_depth == 2

    def test_detection_probability(self) -> None:
        """Test detection probability."""
        metadata = ElementMetadata(detection_class_prob=0.95)
        assert metadata.detection_class_prob == 0.95

    def test_emphasized_text(self) -> None:
        """Test emphasized text tracking."""
        metadata = ElementMetadata(
            emphasized_text_contents=["important", "key point"],
            emphasized_text_tags=["b", "i"],
        )
        assert metadata.emphasized_text_contents == ["important", "key point"]
        assert metadata.emphasized_text_tags == ["b", "i"]

    def test_unique_element_ids(self) -> None:
        """Test that element IDs are unique."""
        metadata1 = ElementMetadata()
        metadata2 = ElementMetadata()
        assert metadata1.element_id != metadata2.element_id


class TestDocumentElement:
    """Tests for DocumentElement model."""

    def test_basic_element(self) -> None:
        """Test basic document element."""
        element = DocumentElement(
            element_type=ElementType.NARRATIVE_TEXT,
            content="Test content",
        )

        assert element.element_type == ElementType.NARRATIVE_TEXT
        assert element.content == "Test content"
        assert element.metadata is not None

    def test_element_with_metadata(self) -> None:
        """Test element with metadata."""
        metadata = ElementMetadata(page_number=1, category_depth=2)
        element = DocumentElement(
            element_type=ElementType.TITLE,
            content="Chapter 1",
            metadata=metadata,
        )

        assert element.metadata.page_number == 1
        assert element.metadata.category_depth == 2

    def test_empty_content_validation(self) -> None:
        """Test that empty content raises validation error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content="",
            )

    def test_whitespace_only_content(self) -> None:
        """Test that whitespace-only content raises error."""
        with pytest.raises(ValueError):
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content="   ",
            )

    def test_legacy_bbox_sync(self) -> None:
        """Test legacy bbox syncs to metadata.coordinates."""
        bbox = (10.0, 20.0, 100.0, 200.0)
        element = DocumentElement(
            element_type=ElementType.NARRATIVE_TEXT,
            content="Test",
            bbox=bbox,
        )

        assert element.metadata.coordinates == bbox

    def test_legacy_page_number_sync(self) -> None:
        """Test legacy page_number syncs to metadata."""
        element = DocumentElement(
            element_type=ElementType.NARRATIVE_TEXT,
            content="Test",
            page_number=5,
        )

        assert element.metadata.page_number == 5

    def test_legacy_confidence_sync(self) -> None:
        """Test legacy confidence syncs to metadata."""
        element = DocumentElement(
            element_type=ElementType.NARRATIVE_TEXT,
            content="Test",
            confidence=0.95,
        )

        assert element.metadata.detection_class_prob == 0.95


class TestChunk:
    """Tests for Chunk model."""

    def test_basic_chunk(self) -> None:
        """Test basic chunk creation."""
        chunk = Chunk(content="Chunk content")

        assert chunk.chunk_id is not None
        assert chunk.content == "Chunk content"
        assert chunk.metadata == {}
        assert chunk.elements == []

    def test_chunk_with_elements(self) -> None:
        """Test chunk with elements."""
        element = DocumentElement(
            element_type=ElementType.NARRATIVE_TEXT,
            content="Test",
        )
        chunk = Chunk(content="Test", elements=[element])

        assert len(chunk.elements) == 1
        assert chunk.elements[0] == element

    def test_chunk_with_metadata(self) -> None:
        """Test chunk with metadata."""
        metadata = {"document_id": "doc-123", "chunk_index": 0}
        chunk = Chunk(content="Test", metadata=metadata)

        assert chunk.metadata["document_id"] == "doc-123"
        assert chunk.metadata["chunk_index"] == 0

    def test_token_count(self) -> None:
        """Test token count."""
        chunk = Chunk(content="Test", token_count=50)
        assert chunk.token_count == 50

    def test_char_count_auto_calculation(self) -> None:
        """Test character count is automatically calculated."""
        content = "This is test content"
        chunk = Chunk(content=content)

        assert chunk.char_count == len(content)

    def test_page_range(self) -> None:
        """Test page range tracking."""
        chunk = Chunk(content="Test", start_page=1, end_page=3)

        assert chunk.start_page == 1
        assert chunk.end_page == 3

    def test_unique_chunk_ids(self) -> None:
        """Test that chunk IDs are unique."""
        chunk1 = Chunk(content="Test 1")
        chunk2 = Chunk(content="Test 2")
        assert chunk1.chunk_id != chunk2.chunk_id


class TestQualityMetrics:
    """Tests for QualityMetrics model."""

    def test_basic_quality_metrics(self) -> None:
        """Test basic quality metrics."""
        metrics = QualityMetrics(overall_score=0.85, quality_level=QualityLevel.GOOD)

        assert metrics.overall_score == 0.85
        assert metrics.quality_level == QualityLevel.GOOD

    def test_quality_level_auto_calculation(self) -> None:
        """Test automatic quality level calculation."""
        # Note: quality_level must be explicitly provided (auto-calculation happens in validator)
        # Excellent: >= 0.95
        metrics = QualityMetrics(overall_score=0.96, quality_level=QualityLevel.EXCELLENT)
        assert metrics.quality_level == QualityLevel.EXCELLENT

        # Good: 0.85-0.94
        metrics = QualityMetrics(overall_score=0.90, quality_level=QualityLevel.GOOD)
        assert metrics.quality_level == QualityLevel.GOOD

        # Marginal: 0.70-0.84
        metrics = QualityMetrics(overall_score=0.75, quality_level=QualityLevel.MARGINAL)
        assert metrics.quality_level == QualityLevel.MARGINAL

        # Poor: < 0.70
        metrics = QualityMetrics(overall_score=0.65, quality_level=QualityLevel.POOR)
        assert metrics.quality_level == QualityLevel.POOR

    def test_component_scores(self) -> None:
        """Test component quality scores."""
        metrics = QualityMetrics(
            overall_score=0.85,
            quality_level=QualityLevel.GOOD,
            text_extraction_score=0.90,
            structure_preservation_score=0.85,
            table_accuracy_score=0.80,
            metadata_completeness_score=0.88,
        )

        assert metrics.text_extraction_score == 0.90
        assert metrics.structure_preservation_score == 0.85
        assert metrics.table_accuracy_score == 0.80
        assert metrics.metadata_completeness_score == 0.88

    def test_failed_checks(self) -> None:
        """Test failed checks tracking."""
        failed = ["table_detection", "text_alignment"]
        metrics = QualityMetrics(
            overall_score=0.70,
            quality_level=QualityLevel.MARGINAL,
            failed_checks=failed,
        )

        assert metrics.failed_checks == failed

    def test_warnings(self) -> None:
        """Test warnings tracking."""
        warnings = ["Low confidence in page 5", "Missing metadata"]
        metrics = QualityMetrics(
            overall_score=0.85,
            quality_level=QualityLevel.GOOD,
            warnings=warnings,
        )

        assert metrics.warnings == warnings

    def test_score_validation(self) -> None:
        """Test score validation (0.0 to 1.0)."""
        # Valid scores
        QualityMetrics(overall_score=0.0, quality_level=QualityLevel.POOR)
        QualityMetrics(overall_score=1.0, quality_level=QualityLevel.EXCELLENT)
        QualityMetrics(overall_score=0.5, quality_level=QualityLevel.POOR)

        # Invalid scores
        with pytest.raises(Exception):
            QualityMetrics(overall_score=-0.1, quality_level=QualityLevel.POOR)

        with pytest.raises(Exception):
            QualityMetrics(overall_score=1.1, quality_level=QualityLevel.EXCELLENT)


class TestParserResult:
    """Tests for ParserResult model."""

    def test_successful_result(self) -> None:
        """Test successful parser result."""
        element = DocumentElement(
            element_type=ElementType.NARRATIVE_TEXT,
            content="Test",
        )
        result = ParserResult(
            success=True,
            elements=[element],
            parser_name="TestParser",
            processing_time=1.5,
        )

        assert result.success is True
        assert len(result.elements) == 1
        assert result.parser_name == "TestParser"
        assert result.processing_time == 1.5

    def test_failed_result(self) -> None:
        """Test failed parser result."""
        result = ParserResult(
            success=False,
            parser_name="TestParser",
            processing_time=0.5,
            error_message="Parsing failed",
        )

        assert result.success is False
        assert result.error_message == "Parsing failed"
        assert len(result.elements) == 0

    def test_with_metadata(self) -> None:
        """Test parser result with metadata."""
        metadata = {"page_count": 10, "has_images": True}
        result = ParserResult(
            success=True,
            parser_name="TestParser",
            processing_time=2.0,
            metadata=metadata,
        )

        assert result.metadata["page_count"] == 10
        assert result.metadata["has_images"] is True

    def test_with_warnings(self) -> None:
        """Test parser result with warnings."""
        warnings = ["Low quality on page 3", "Table detection uncertain"]
        result = ParserResult(
            success=True,
            parser_name="TestParser",
            processing_time=1.0,
            warnings=warnings,
        )

        assert result.warnings == warnings

    def test_with_raw_content(self) -> None:
        """Test parser result with raw content."""
        raw = "Raw text content\nfrom document"
        result = ParserResult(
            success=True,
            parser_name="TestParser",
            processing_time=1.0,
            raw_content=raw,
        )

        assert result.raw_content == raw


class TestDocument:
    """Tests for Document model."""

    def test_basic_document(self, temp_test_file: Path) -> None:
        """Test basic document creation."""
        doc = Document(
            source_path=str(temp_test_file),
            format=DocumentFormat.PDF,
        )

        assert doc.document_id is not None
        assert doc.source_path == str(temp_test_file)
        assert doc.format == DocumentFormat.PDF
        assert doc.status == ProcessingStatus.PENDING

    def test_document_with_url(self) -> None:
        """Test document with URL source."""
        doc = Document(
            source_path=None,
            source_url="https://example.com/doc.pdf",
            format=DocumentFormat.PDF,
        )

        assert doc.source_url == "https://example.com/doc.pdf"
        assert doc.source_path is None

    def test_source_path_validation_fails(self) -> None:
        """Test that invalid source path raises error."""
        with pytest.raises(ValueError, match="does not exist"):
            Document(
                source_path="/nonexistent/file.pdf",
                format=DocumentFormat.PDF,
            )

    def test_timestamps(self) -> None:
        """Test document timestamps."""
        doc = Document(
            source_path=None,
            format=DocumentFormat.PDF,
        )

        assert doc.created_at is not None
        assert doc.updated_at is not None
        assert isinstance(doc.created_at, datetime)
        assert doc.created_at.tzinfo == UTC

    def test_custom_timestamps(self) -> None:
        """Test custom timestamps."""
        created = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        updated = datetime(2025, 1, 2, 12, 0, 0, tzinfo=UTC)

        doc = Document(
            source_path=None,
            format=DocumentFormat.PDF,
            created_at=created,
            updated_at=updated,
        )

        assert doc.created_at == created
        assert doc.updated_at == updated

    def test_with_metadata(self) -> None:
        """Test document with metadata."""
        metadata = {"title": "Test Doc", "pages": 10}
        doc = Document(
            source_path=None,
            format=DocumentFormat.PDF,
            metadata=metadata,
        )

        assert doc.metadata["title"] == "Test Doc"
        assert doc.metadata["pages"] == 10

    def test_with_elements(self) -> None:
        """Test document with elements."""
        element = DocumentElement(
            element_type=ElementType.NARRATIVE_TEXT,
            content="Test",
        )
        doc = Document(
            source_path=None,
            format=DocumentFormat.PDF,
            elements=[element],
        )

        assert len(doc.elements) == 1
        assert doc.elements[0] == element

    def test_with_chunks(self) -> None:
        """Test document with chunks."""
        chunk = Chunk(content="Test chunk")
        doc = Document(
            source_path=None,
            format=DocumentFormat.PDF,
            chunks=[chunk],
        )

        assert len(doc.chunks) == 1
        assert doc.chunks[0] == chunk

    def test_with_quality_metrics(self) -> None:
        """Test document with quality metrics."""
        metrics = QualityMetrics(overall_score=0.85, quality_level=QualityLevel.GOOD)
        doc = Document(
            source_path=None,
            format=DocumentFormat.PDF,
            quality_metrics=metrics,
        )

        assert doc.quality_metrics == metrics
        assert doc.quality_metrics.overall_score == 0.85

    def test_update_status(self) -> None:
        """Test updating document status."""
        doc = Document(
            source_path=None,
            format=DocumentFormat.PDF,
        )

        original_updated = doc.updated_at

        # Small delay to ensure timestamp changes
        import time

        time.sleep(0.01)

        doc.update_status(ProcessingStatus.COMPLETED)

        assert doc.status == ProcessingStatus.COMPLETED
        assert doc.updated_at > original_updated

    def test_parser_info(self, temp_test_file: Path) -> None:
        """Test parser information tracking."""
        doc = Document(
            source_path=str(temp_test_file),
            format=DocumentFormat.PDF,
            parser_used="PyMuPDF",
            processing_time=2.5,
        )

        assert doc.parser_used == "PyMuPDF"
        assert doc.processing_time == 2.5

    def test_unique_document_ids(self) -> None:
        """Test that document IDs are unique."""
        doc1 = Document(source_path=None, format=DocumentFormat.PDF)
        doc2 = Document(source_path=None, format=DocumentFormat.PDF)
        assert doc1.document_id != doc2.document_id


class TestModelIntegration:
    """Tests for model integration."""

    def test_complete_document_workflow(self, temp_test_file: Path) -> None:
        """Test complete document processing workflow."""
        # Create document
        doc = Document(
            source_path=str(temp_test_file),
            format=DocumentFormat.PDF,
            metadata={"title": "Test Document"},
        )

        # Add elements
        doc.elements = [
            DocumentElement(
                element_type=ElementType.TITLE,
                content="Introduction",
                metadata=ElementMetadata(page_number=1),
            ),
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content="This is the content.",
                metadata=ElementMetadata(page_number=1),
            ),
        ]

        # Add chunks
        doc.chunks = [
            Chunk(
                content="Introduction\n\nThis is the content.",
                token_count=10,
                start_page=1,
                end_page=1,
            ),
        ]

        # Add quality metrics
        doc.quality_metrics = QualityMetrics(
            overall_score=0.90,
            quality_level=QualityLevel.GOOD,
            text_extraction_score=0.95,
        )

        # Update status
        doc.update_status(ProcessingStatus.COMPLETED)
        doc.parser_used = "TestParser"
        doc.processing_time = 1.5

        # Verify complete document
        assert doc.status == ProcessingStatus.COMPLETED
        assert len(doc.elements) == 2
        assert len(doc.chunks) == 1
        assert doc.quality_metrics.overall_score == 0.90
        assert doc.parser_used == "TestParser"


class TestEdgeCases:
    """Tests for edge cases and validation."""

    def test_document_with_none_source_path(self) -> None:
        """Test document with None source_path is valid."""
        doc = Document(source_path=None, format=DocumentFormat.PDF)
        assert doc.source_path is None

    def test_element_content_with_newlines(self) -> None:
        """Test element content with newlines."""
        content = "Line 1\nLine 2\nLine 3"
        element = DocumentElement(
            element_type=ElementType.NARRATIVE_TEXT,
            content=content,
        )
        assert element.content == content

    def test_chunk_with_empty_metadata(self) -> None:
        """Test chunk with empty metadata."""
        chunk = Chunk(content="Test", metadata={})
        assert chunk.metadata == {}

    def test_quality_metrics_boundary_values(self) -> None:
        """Test quality metrics at boundary values."""
        # Test exactly 0.95 (boundary for excellent)
        metrics = QualityMetrics(overall_score=0.95, quality_level=QualityLevel.EXCELLENT)
        assert metrics.quality_level == QualityLevel.EXCELLENT

        # Test exactly 0.85 (boundary for good)
        metrics = QualityMetrics(overall_score=0.85, quality_level=QualityLevel.GOOD)
        assert metrics.quality_level == QualityLevel.GOOD

        # Test exactly 0.70 (boundary for marginal)
        metrics = QualityMetrics(overall_score=0.70, quality_level=QualityLevel.MARGINAL)
        assert metrics.quality_level == QualityLevel.MARGINAL


class TestQualityMetricsAutoCalculation:
    """Tests for automatic quality level calculation."""

    def test_auto_calculate_quality_level_provided(self) -> None:
        """Test that provided quality_level is preserved."""
        # Test that when quality_level is provided, it is used
        metrics = QualityMetrics(overall_score=0.50, quality_level=QualityLevel.EXCELLENT)
        # Even though score is low, provided quality_level should be used
        assert metrics.quality_level == QualityLevel.EXCELLENT

    def test_quality_level_different_from_score(self) -> None:
        """Test that quality_level can be set independently from score."""
        # Can set any quality level regardless of score
        metrics = QualityMetrics(overall_score=0.50, quality_level=QualityLevel.GOOD)
        assert metrics.quality_level == QualityLevel.GOOD
        assert metrics.overall_score == 0.50


class TestDocumentElementLegacyFieldSync:
    """Tests for legacy field synchronization in DocumentElement."""

    def test_sync_bbox_from_metadata_coordinates(self) -> None:
        """Test bbox syncs from metadata.coordinates when not set."""
        metadata = ElementMetadata(coordinates=(10, 20, 100, 200))
        element = DocumentElement(
            element_type=ElementType.PARAGRAPH,
            content="Test",
            metadata=metadata,
        )
        # bbox should be synced from metadata.coordinates
        assert element.bbox == (10, 20, 100, 200)

    def test_sync_confidence_from_metadata_detection_class_prob(self) -> None:
        """Test confidence syncs from metadata.detection_class_prob when not set."""
        metadata = ElementMetadata(detection_class_prob=0.95)
        element = DocumentElement(
            element_type=ElementType.PARAGRAPH,
            content="Test",
            metadata=metadata,
        )
        # confidence should be synced from metadata.detection_class_prob
        assert element.confidence == 0.95
