"""Comprehensive tests for document routing and parser registry."""

from pathlib import Path

import pytest

from data_ingestor.core.base import BaseParser
from data_ingestor.core.config import Settings
from data_ingestor.core.exceptions import ParserError, UnsupportedFormatError
from data_ingestor.core.models import (
    Document,
    DocumentFormat,
    ParserResult,
    ProcessingStatus,
)
from data_ingestor.pipeline.router import DocumentRouter, ParserRegistry


class TestParserRegistry:
    """Tests for ParserRegistry class."""

    def test_registry_initialization(self) -> None:
        """Test registry initializes with empty parser lists."""
        registry = ParserRegistry()
        assert registry.get_parsers(DocumentFormat.PDF) == []
        assert registry.get_parsers(DocumentFormat.DOCX) == []
        assert registry.get_parsers(DocumentFormat.HTML) == []

    def test_register_single_parser(self, mock_parser_class) -> None:
        """Test registering a single parser for one format."""
        registry = ParserRegistry()
        parser = mock_parser_class({"name": "TestParser", "priority": 10})

        registry.register(parser, [DocumentFormat.PDF])

        parsers = registry.get_parsers(DocumentFormat.PDF)
        assert len(parsers) == 1
        assert parsers[0].name == "TestParser"

    def test_register_parser_multiple_formats(self, mock_parser_class) -> None:
        """Test registering parser for multiple formats."""
        registry = ParserRegistry()
        parser = mock_parser_class({"name": "MultiFormatParser"})

        registry.register(parser, [DocumentFormat.PDF, DocumentFormat.DOCX])

        assert len(registry.get_parsers(DocumentFormat.PDF)) == 1
        assert len(registry.get_parsers(DocumentFormat.DOCX)) == 1

    def test_register_multiple_parsers_with_priority(self, mock_parser_class) -> None:
        """Test that parsers are ordered by priority."""
        registry = ParserRegistry()

        # Register parsers in reverse priority order
        parser_low = mock_parser_class({"name": "LowPriority", "priority": 50})
        parser_high = mock_parser_class({"name": "HighPriority", "priority": 10})
        parser_mid = mock_parser_class({"name": "MidPriority", "priority": 30})

        registry.register(parser_low, [DocumentFormat.PDF])
        registry.register(parser_high, [DocumentFormat.PDF])
        registry.register(parser_mid, [DocumentFormat.PDF])

        parsers = registry.get_parsers(DocumentFormat.PDF)
        assert len(parsers) == 3
        assert parsers[0].name == "HighPriority"
        assert parsers[1].name == "MidPriority"
        assert parsers[2].name == "LowPriority"

    def test_get_primary_parser(self, mock_parser_class) -> None:
        """Test getting the highest priority parser."""
        registry = ParserRegistry()

        parser1 = mock_parser_class({"name": "Parser1", "priority": 50})
        parser2 = mock_parser_class({"name": "Parser2", "priority": 10})

        registry.register(parser1, [DocumentFormat.PDF])
        registry.register(parser2, [DocumentFormat.PDF])

        primary = registry.get_primary_parser(DocumentFormat.PDF)
        assert primary is not None
        assert primary.name == "Parser2"  # Lower priority number = higher priority

    def test_get_primary_parser_no_parsers(self) -> None:
        """Test getting primary parser when none registered."""
        registry = ParserRegistry()
        primary = registry.get_primary_parser(DocumentFormat.PDF)
        assert primary is None

    def test_health_check_all_healthy(self, mock_parser_class) -> None:
        """Test health check when all parsers are healthy."""
        registry = ParserRegistry()

        parser1 = mock_parser_class({"name": "Parser1"})
        parser2 = mock_parser_class({"name": "Parser2"})

        registry.register(parser1, [DocumentFormat.PDF])
        registry.register(parser2, [DocumentFormat.DOCX])

        health = registry.health_check()

        assert "pdf" in health
        assert "docx" in health
        assert len(health["pdf"]) == 1
        assert health["pdf"][0]["healthy"] is True

    def test_health_check_unhealthy_parser(self, mock_parser_class) -> None:
        """Test health check with unhealthy parser."""
        registry = ParserRegistry()

        parser = mock_parser_class({"name": "UnhealthyParser"})
        parser.should_fail = True

        registry.register(parser, [DocumentFormat.PDF])

        health = registry.health_check()
        assert health["pdf"][0]["healthy"] is False

    def test_health_check_with_exception(self, mock_parser_class) -> None:
        """Test health check when parser raises exception."""
        registry = ParserRegistry()

        class BadParser(BaseParser):
            def supports_format(self, document_format: DocumentFormat) -> bool:
                return True

            def parse(self, document: Document) -> ParserResult:
                return ParserResult(success=True, parser_name="BadParser", processing_time=0.1)

            def health_check(self) -> bool:
                raise RuntimeError("Health check failed")

        parser = BadParser()
        registry.register(parser, [DocumentFormat.PDF])

        health = registry.health_check()
        assert health["pdf"][0]["healthy"] is False
        assert "error" in health["pdf"][0]


class TestDocumentRouterInitialization:
    """Tests for DocumentRouter initialization."""

    def test_router_initialization_default(self) -> None:
        """Test router initializes with default settings."""
        router = DocumentRouter()
        assert router.settings is not None
        assert router.format_detector is not None
        assert router.parser_registry is not None

    def test_router_initialization_custom_settings(self) -> None:
        """Test router with custom settings."""
        settings = Settings(debug=True, max_file_size_mb=100)
        router = DocumentRouter(settings=settings)
        assert router.settings.debug is True
        assert router.settings.max_file_size_mb == 100


class TestDocumentCreation:
    """Tests for document creation."""

    def test_create_document_from_path(self, temp_test_file: Path) -> None:
        """Test creating document from file path."""
        router = DocumentRouter()
        doc = router.create_document(source_path=temp_test_file)

        assert doc.document_id is not None
        assert doc.source_path is not None
        assert doc.format == DocumentFormat.PDF
        assert doc.status == ProcessingStatus.PENDING

    def test_create_document_from_url(self) -> None:
        """Test creating document from URL."""
        router = DocumentRouter()
        doc = router.create_document(source_url="https://example.com/document.pdf")

        assert doc.document_id is not None
        assert doc.source_url == "https://example.com/document.pdf"
        assert doc.format == DocumentFormat.PDF

    def test_create_document_with_metadata(self, temp_test_file: Path) -> None:
        """Test creating document with custom metadata."""
        router = DocumentRouter()
        metadata = {"title": "Test Document", "author": "Test Author"}
        doc = router.create_document(source_path=temp_test_file, metadata=metadata)

        assert doc.metadata["title"] == "Test Document"
        assert doc.metadata["author"] == "Test Author"

    def test_create_document_no_source(self) -> None:
        """Test that creating document without source raises error."""
        router = DocumentRouter()
        with pytest.raises(ValueError, match="Either source_path or source_url"):
            router.create_document()

    def test_create_document_unknown_format(self, tmp_path: Path) -> None:
        """Test handling of unknown format."""
        # Create file with unknown extension
        unknown_file = tmp_path / "test.unknown_ext"
        unknown_file.write_text("test content")

        router = DocumentRouter()
        with pytest.raises(UnsupportedFormatError):
            router.create_document(source_path=unknown_file)


class TestDeduplication:
    """Tests for document deduplication."""

    def test_is_duplicate_first_time(self, temp_test_file: Path) -> None:
        """Test that first occurrence is not marked as duplicate."""
        router = DocumentRouter()
        doc = router.create_document(source_path=temp_test_file)

        is_dup = router.is_duplicate(doc)
        assert is_dup is False

    def test_is_duplicate_second_time(self, temp_test_file: Path) -> None:
        """Test that second occurrence is marked as duplicate."""
        router = DocumentRouter()
        doc = router.create_document(source_path=temp_test_file)

        # First check
        router.is_duplicate(doc)

        # Second check - should be duplicate
        is_dup = router.is_duplicate(doc)
        assert is_dup is True

    def test_is_duplicate_no_source_path(self) -> None:
        """Test duplicate check for document without source path."""
        router = DocumentRouter()
        doc = Document(
            source_path=None,
            source_url="https://example.com",
            format=DocumentFormat.HTML,
        )

        is_dup = router.is_duplicate(doc)
        assert is_dup is False

    def test_is_duplicate_nonexistent_file(self) -> None:
        """Test duplicate check for nonexistent file."""
        router = DocumentRouter()
        doc = Document(source_path=None, format=DocumentFormat.PDF)
        doc.source_path = "/nonexistent/file.pdf"
        is_dup = router.is_duplicate(doc)
        assert is_dup is False


class TestDocumentRouting:
    """Tests for document routing to parsers."""

    def test_route_document_success(self, configured_router: DocumentRouter, temp_test_file: Path) -> None:
        """Test successful document routing."""
        doc = configured_router.create_document(source_path=temp_test_file)
        result = configured_router.route_document(doc)

        assert result.success is True
        assert doc.status == ProcessingStatus.COMPLETED
        assert doc.parser_used is not None

    def test_route_document_no_parser_available(self) -> None:
        """Test routing when no parser is available."""
        router = DocumentRouter()
        doc = Document(
            source_path=None,
            format=DocumentFormat.PDF,
        )

        with pytest.raises(UnsupportedFormatError):
            router.route_document(doc)

    def test_route_document_fallback_to_secondary(
        self,
        mock_parser_class,
        temp_test_file: Path,
    ) -> None:
        """Test fallback to secondary parser when primary fails."""
        router = DocumentRouter()

        # Register primary parser that will fail
        primary_parser = mock_parser_class({"name": "PrimaryParser", "priority": 10})
        primary_parser.should_fail = True
        router.parser_registry.register(primary_parser, [DocumentFormat.PDF])

        # Register secondary parser that will succeed
        secondary_parser = mock_parser_class({"name": "SecondaryParser", "priority": 20})
        router.parser_registry.register(secondary_parser, [DocumentFormat.PDF])

        doc = router.create_document(source_path=temp_test_file)
        result = router.route_document(doc)

        assert result.success is True
        assert doc.parser_used == "SecondaryParser"

    def test_route_document_all_parsers_fail(
        self,
        mock_parser_class,
        temp_test_file: Path,
    ) -> None:
        """Test that error is raised when all parsers fail."""
        router = DocumentRouter()

        # Register multiple failing parsers
        parser1 = mock_parser_class({"name": "Parser1", "priority": 10})
        parser1.should_fail = True
        parser2 = mock_parser_class({"name": "Parser2", "priority": 20})
        parser2.should_fail = True

        router.parser_registry.register(parser1, [DocumentFormat.PDF])
        router.parser_registry.register(parser2, [DocumentFormat.PDF])

        doc = router.create_document(source_path=temp_test_file)

        with pytest.raises(ParserError) as exc_info:
            router.route_document(doc)

        assert doc.status == ProcessingStatus.FAILED
        assert "all" in str(exc_info.value.message).lower()

    def test_route_document_validation_failure(
        self,
        mock_parser_class,
        temp_test_file: Path,
    ) -> None:
        """Test routing when document validation fails."""
        router = DocumentRouter()
        # Create parser with restrictive size limit
        parser = mock_parser_class({"name": "RestrictiveParser", "max_file_size_mb": 0.0001})
        router.parser_registry.register(parser, [DocumentFormat.PDF])
        doc = router.create_document(source_path=temp_test_file)
        # Should fail due to no parsers passing validation
        with pytest.raises(ParserError):
            router.route_document(doc)


class TestEndToEndProcessing:
    """Tests for end-to-end document processing."""

    def test_process_document_success(self, configured_router: DocumentRouter, temp_test_file: Path) -> None:
        """Test successful end-to-end processing."""
        doc, result = configured_router.process_document(source_path=temp_test_file)

        assert doc is not None
        assert result.success is True
        assert doc.status == ProcessingStatus.COMPLETED

    def test_process_document_with_url(self, configured_router: DocumentRouter) -> None:
        """Test processing document from URL."""
        # configured_router has parsers for PDF, so URL detection + parsing should work
        # The mock parser will succeed since it doesn't require actual file access
        doc, result = configured_router.process_document(source_url="https://example.com/doc.pdf")
        assert doc is not None
        assert result.success is True  # Mock parser always succeeds

    def test_process_document_duplicate_detection(
        self,
        configured_router: DocumentRouter,
        temp_test_file: Path,
    ) -> None:
        """Test that duplicate documents are detected."""
        # Process first time
        doc1, result1 = configured_router.process_document(source_path=temp_test_file)
        assert result1.success is True

        # Process second time - should be detected as duplicate
        doc2, result2 = configured_router.process_document(source_path=temp_test_file)
        assert result2.metadata.get("duplicate") is True
        assert result2.metadata.get("cached") is True

    def test_process_document_skip_duplicate_check(
        self,
        configured_router: DocumentRouter,
        temp_test_file: Path,
    ) -> None:
        """Test processing with duplicate check disabled."""
        # Process first time
        configured_router.process_document(source_path=temp_test_file)

        # Process second time with skip_duplicate_check
        doc2, result2 = configured_router.process_document(
            source_path=temp_test_file,
            skip_duplicate_check=True,
        )
        assert result2.success is True
        assert result2.metadata.get("duplicate") is not True

    def test_process_document_with_metadata(
        self,
        configured_router: DocumentRouter,
        temp_test_file: Path,
    ) -> None:
        """Test processing document with custom metadata."""
        metadata = {"custom_field": "custom_value"}
        doc, result = configured_router.process_document(
            source_path=temp_test_file,
            metadata=metadata,
        )

        assert doc.metadata["custom_field"] == "custom_value"

    def test_process_document_no_source(self, configured_router: DocumentRouter) -> None:
        """Test that processing without source raises error."""
        with pytest.raises(ValueError):
            configured_router.process_document()


class TestParserIntegration:
    """Tests for parser integration with router."""

    def test_parser_receives_document(self, mock_parser_class, temp_test_file: Path) -> None:
        """Test that parser receives correct document."""
        router = DocumentRouter()
        parser = mock_parser_class({"name": "TestParser"})
        router.parser_registry.register(parser, [DocumentFormat.PDF])

        doc = router.create_document(source_path=temp_test_file)
        result = router.route_document(doc)

        assert parser.parse_call_count == 1
        assert result.parser_name == "TestParser"

    def test_document_updated_with_parser_result(
        self,
        configured_router: DocumentRouter,
        temp_test_file: Path,
    ) -> None:
        """Test that document is updated with parser results."""
        doc = configured_router.create_document(source_path=temp_test_file)
        configured_router.route_document(doc)

        assert len(doc.elements) > 0
        assert doc.parser_used is not None
        assert doc.processing_time is not None


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_parser_registry(self) -> None:
        """Test router behavior with no parsers registered."""
        router = DocumentRouter()
        doc = Document(source_path=None, format=DocumentFormat.PDF)

        with pytest.raises(UnsupportedFormatError):
            router.route_document(doc)

    def test_parser_exception_handling(self, mock_parser_class, temp_test_file: Path) -> None:
        """Test handling of parser exceptions."""
        router = DocumentRouter()

        class ExceptionParser(BaseParser):
            def supports_format(self, document_format: DocumentFormat) -> bool:
                return document_format == DocumentFormat.PDF

            def parse(self, document: Document) -> ParserResult:
                raise RuntimeError("Parser crashed")

            def health_check(self) -> bool:
                return True

        parser = ExceptionParser()
        router.parser_registry.register(parser, [DocumentFormat.PDF])

        doc = router.create_document(source_path=temp_test_file)

        with pytest.raises(ParserError):
            router.route_document(doc)

    def test_concurrent_processing_different_docs(
        self,
        configured_router: DocumentRouter,
        temp_test_file: Path,
    ) -> None:
        """Test processing multiple different documents."""
        doc1, result1 = configured_router.process_document(source_path=temp_test_file)
        doc2, result2 = configured_router.process_document(source_path=temp_test_file)

        # Same file should trigger duplicate detection
        assert result2.metadata.get("duplicate") is True
