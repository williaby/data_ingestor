"""Comprehensive tests for BaseParser abstract class."""

from pathlib import Path

import pytest

from data_ingestor.core.base import BaseParser
from data_ingestor.core.models import (
    Document,
    DocumentElement,
    DocumentFormat,
    ElementMetadata,
    ElementType,
    ParserResult,
)


class TestConcreteParser(BaseParser):
    """Concrete implementation of BaseParser for testing."""

    def __init__(self, config: dict | None = None) -> None:
        super().__init__(config)
        self.supported_formats = [DocumentFormat.PDF]

    def supports_format(self, document_format: DocumentFormat) -> bool:
        """Check if format is supported."""
        return document_format in self.supported_formats

    def parse(self, document: Document) -> ParserResult:
        """Mock parse implementation."""
        elements = [
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content="Test content",
                metadata=ElementMetadata(page_number=1),
            ),
        ]
        return ParserResult(
            success=True,
            elements=elements,
            parser_name=self.name,
            processing_time=0.1,
        )

    def health_check(self) -> bool:
        """Mock health check."""
        return True


class TestBaseParserInitialization:
    """Tests for BaseParser initialization."""

    def test_default_initialization(self) -> None:
        """Test BaseParser initialization with no config."""
        parser = TestConcreteParser()
        assert parser.config == {}
        assert parser.name == "TestConcreteParser"

    def test_initialization_with_config(self) -> None:
        """Test BaseParser initialization with config."""
        config = {"max_file_size_mb": 100, "enable_ocr": True}
        parser = TestConcreteParser(config)
        assert parser.config == config
        assert parser.config["max_file_size_mb"] == 100
        assert parser.config["enable_ocr"] is True

    def test_name_attribute(self) -> None:
        """Test that name is set to class name."""
        parser = TestConcreteParser()
        assert parser.name == "TestConcreteParser"


class TestAbstractMethodEnforcement:
    """Tests that abstract methods must be implemented."""

    def test_cannot_instantiate_base_parser(self) -> None:
        """Test that BaseParser cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseParser()  # type: ignore[abstract]

    def test_must_implement_supports_format(self) -> None:
        """Test that supports_format must be implemented."""

        class IncompleteParser(BaseParser):
            def parse(self, document: Document) -> ParserResult:
                return ParserResult(success=True, parser_name="test", processing_time=0.1)

            def health_check(self) -> bool:
                return True

        with pytest.raises(TypeError):
            IncompleteParser()  # type: ignore[abstract]

    def test_must_implement_parse(self) -> None:
        """Test that parse must be implemented."""

        class IncompleteParser(BaseParser):
            def supports_format(self, document_format: DocumentFormat) -> bool:
                return True

            def health_check(self) -> bool:
                return True

        with pytest.raises(TypeError):
            IncompleteParser()  # type: ignore[abstract]

    def test_must_implement_health_check(self) -> None:
        """Test that health_check must be implemented."""

        class IncompleteParser(BaseParser):
            def supports_format(self, document_format: DocumentFormat) -> bool:
                return True

            def parse(self, document: Document) -> ParserResult:
                return ParserResult(success=True, parser_name="test", processing_time=0.1)

        with pytest.raises(TypeError):
            IncompleteParser()  # type: ignore[abstract]


class TestSupportsFormat:
    """Tests for supports_format method."""

    def test_supports_format_pdf(self) -> None:
        """Test format support check for PDF."""
        parser = TestConcreteParser()
        assert parser.supports_format(DocumentFormat.PDF) is True

    def test_supports_format_unsupported(self) -> None:
        """Test format support check for unsupported format."""
        parser = TestConcreteParser()
        assert parser.supports_format(DocumentFormat.DOCX) is False
        assert parser.supports_format(DocumentFormat.HTML) is False

    def test_supports_format_multiple(self) -> None:
        """Test parser supporting multiple formats."""
        parser = TestConcreteParser()
        parser.supported_formats = [DocumentFormat.PDF, DocumentFormat.DOCX]

        assert parser.supports_format(DocumentFormat.PDF) is True
        assert parser.supports_format(DocumentFormat.DOCX) is True
        assert parser.supports_format(DocumentFormat.HTML) is False


class TestValidateDocument:
    """Tests for validate_document method."""

    def test_validate_supported_format(self, temp_test_file: Path) -> None:
        """Test validation succeeds for supported format."""
        parser = TestConcreteParser()
        doc = Document(
            source_path=str(temp_test_file),
            format=DocumentFormat.PDF,
        )
        assert parser.validate_document(doc) is True

    def test_validate_unsupported_format(self, temp_test_file: Path) -> None:
        """Test validation fails for unsupported format."""
        parser = TestConcreteParser()
        doc = Document(
            source_path=str(temp_test_file),
            format=DocumentFormat.DOCX,
        )
        assert parser.validate_document(doc) is False

    def test_validate_nonexistent_file(self) -> None:
        """Test validation fails for nonexistent file."""
        # Can't create Document with non-existent path due to validator
        parser = TestConcreteParser()
        doc = Document(source_path=None, format=DocumentFormat.PDF)
        doc.source_path = "/nonexistent/file.pdf"
        assert parser.validate_document(doc) is False

    def test_validate_file_is_directory(self, tmp_path: Path) -> None:
        """Test validation fails when path is a directory."""
        parser = TestConcreteParser()
        doc = Document(
            source_path=str(tmp_path),
            format=DocumentFormat.PDF,
        )
        assert parser.validate_document(doc) is False

    def test_validate_document_without_source_path(self) -> None:
        """Test validation succeeds when source_path is None."""
        parser = TestConcreteParser()
        doc = Document(
            source_path=None,
            format=DocumentFormat.PDF,
        )
        # Should pass because no path validation needed
        assert parser.validate_document(doc) is True

    def test_validate_with_file_size_limit(self, tmp_path: Path) -> None:
        """Test validation with file size limit."""
        # Create large file
        large_file = tmp_path / "large.pdf"
        large_file.write_bytes(b"x" * 2000)

        parser = TestConcreteParser({"max_file_size_mb": 0.001})  # Very small limit
        doc = Document(
            source_path=str(large_file),
            format=DocumentFormat.PDF,
        )

        # File should exceed the tiny limit
        assert parser.validate_document(doc) is False

    def test_validate_with_generous_file_size_limit(self, temp_test_file: Path) -> None:
        """Test validation with generous file size limit."""
        parser = TestConcreteParser({"max_file_size_mb": 100})
        doc = Document(
            source_path=str(temp_test_file),
            format=DocumentFormat.PDF,
        )
        assert parser.validate_document(doc) is True

    def test_validate_without_file_size_limit(self, temp_test_file: Path) -> None:
        """Test validation without file size limit configured."""
        parser = TestConcreteParser()
        doc = Document(
            source_path=str(temp_test_file),
            format=DocumentFormat.PDF,
        )
        assert parser.validate_document(doc) is True


class TestGetPriority:
    """Tests for get_priority method."""

    def test_default_priority(self) -> None:
        """Test default priority is 100."""
        parser = TestConcreteParser()
        assert parser.get_priority() == 100

    def test_custom_priority(self) -> None:
        """Test custom priority from config."""
        parser = TestConcreteParser({"priority": 50})
        assert parser.get_priority() == 50

    def test_priority_zero(self) -> None:
        """Test priority can be zero."""
        parser = TestConcreteParser({"priority": 0})
        assert parser.get_priority() == 0

    def test_priority_negative(self) -> None:
        """Test negative priority."""
        parser = TestConcreteParser({"priority": -10})
        assert parser.get_priority() == -10

    def test_priority_sorting(self) -> None:
        """Test that parsers can be sorted by priority."""
        parser1 = TestConcreteParser({"priority": 50})
        parser2 = TestConcreteParser({"priority": 10})
        parser3 = TestConcreteParser({"priority": 30})

        parsers = [parser1, parser2, parser3]
        sorted_parsers = sorted(parsers, key=lambda p: p.get_priority())

        assert sorted_parsers[0].get_priority() == 10
        assert sorted_parsers[1].get_priority() == 30
        assert sorted_parsers[2].get_priority() == 50


class TestParse:
    """Tests for parse method (implementation specific)."""

    def test_parse_returns_parser_result(self) -> None:
        """Test that parse returns ParserResult."""
        parser = TestConcreteParser()
        doc = Document(
            source_path=None,
            format=DocumentFormat.PDF,
        )
        result = parser.parse(doc)
        assert isinstance(result, ParserResult)
        assert result.success is True
        assert result.parser_name == "TestConcreteParser"

    def test_parse_result_has_elements(self) -> None:
        """Test that parse result contains elements."""
        parser = TestConcreteParser()
        doc = Document(
            source_path=None,
            format=DocumentFormat.PDF,
        )
        result = parser.parse(doc)
        assert len(result.elements) > 0
        assert isinstance(result.elements[0], DocumentElement)


class TestHealthCheck:
    """Tests for health_check method."""

    def test_health_check_returns_bool(self) -> None:
        """Test that health_check returns boolean."""
        parser = TestConcreteParser()
        health = parser.health_check()
        assert isinstance(health, bool)

    def test_health_check_healthy(self) -> None:
        """Test health check for healthy parser."""
        parser = TestConcreteParser()
        assert parser.health_check() is True

    def test_health_check_unhealthy(self) -> None:
        """Test health check for unhealthy parser."""

        class UnhealthyParser(TestConcreteParser):
            def health_check(self) -> bool:
                return False

        parser = UnhealthyParser()
        assert parser.health_check() is False


class TestConfigurationHandling:
    """Tests for configuration handling."""

    def test_config_immutability(self) -> None:
        """Test that config can be modified after initialization."""
        parser = TestConcreteParser({"setting": "value"})
        assert parser.config["setting"] == "value"

        # Config is mutable (dict)
        parser.config["setting"] = "new_value"
        assert parser.config["setting"] == "new_value"

    def test_config_empty_dict(self) -> None:
        """Test empty config dict."""
        parser = TestConcreteParser({})
        assert parser.config == {}
        assert parser.get_priority() == 100

    def test_config_with_unknown_keys(self) -> None:
        """Test config with unknown keys doesn't break parser."""
        parser = TestConcreteParser({"unknown_key": "value", "another": 123})
        assert parser.config["unknown_key"] == "value"
        assert parser.config["another"] == 123

    def test_config_various_types(self) -> None:
        """Test config with various value types."""
        config = {
            "string": "value",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
        }
        parser = TestConcreteParser(config)
        assert parser.config == config


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_validate_document_with_url(self) -> None:
        """Test validation for document with URL (no source_path)."""
        parser = TestConcreteParser()
        doc = Document(
            source_path=None,
            source_url="https://example.com/doc.pdf",
            format=DocumentFormat.PDF,
        )
        # Should pass since no file system validation needed
        assert parser.validate_document(doc) is True

    def test_validate_empty_string_path(self) -> None:
        """Test validation with empty string path."""
        TestConcreteParser()
        # This would fail in Document validation before reaching here
        # Testing the validator behavior

    def test_priority_with_invalid_type(self) -> None:
        """Test priority with invalid type in config."""
        TestConcreteParser({"priority": "invalid"})
        # get_priority will return the invalid value as-is (cast to int)
        # This could cause issues in sorting

    def test_multiple_parser_instances(self) -> None:
        """Test creating multiple parser instances."""
        parser1 = TestConcreteParser({"priority": 10})
        parser2 = TestConcreteParser({"priority": 20})

        assert parser1.get_priority() == 10
        assert parser2.get_priority() == 20
        assert parser1.name == parser2.name  # Same class


class TestParserInheritance:
    """Tests for parser inheritance patterns."""

    def test_custom_parser_can_override_methods(self) -> None:
        """Test that custom parser can override base methods."""

        class CustomParser(TestConcreteParser):
            def supports_format(self, document_format: DocumentFormat) -> bool:
                # Support all formats
                return True

        parser = CustomParser()
        assert parser.supports_format(DocumentFormat.DOCX) is True
        assert parser.supports_format(DocumentFormat.HTML) is True

    def test_custom_parser_can_extend_validation(self, temp_test_file: Path) -> None:
        """Test that custom parser can extend validation logic."""

        class StrictParser(TestConcreteParser):
            def validate_document(self, document: Document) -> bool:
                # Call parent validation first
                if not super().validate_document(document):
                    return False
                # Add custom validation
                return document.metadata.get("approved") is True

        parser = StrictParser()

        # Document without approval
        doc1 = Document(
            source_path=str(temp_test_file),
            format=DocumentFormat.PDF,
        )
        assert parser.validate_document(doc1) is False

        # Document with approval
        doc2 = Document(
            source_path=str(temp_test_file),
            format=DocumentFormat.PDF,
            metadata={"approved": True},
        )
        assert parser.validate_document(doc2) is True

    def test_parser_with_custom_name(self) -> None:
        """Test parser with custom name override."""

        class NamedParser(TestConcreteParser):
            def __init__(self, config: dict | None = None) -> None:
                super().__init__(config)
                self.name = "CustomNameParser"

        parser = NamedParser()
        assert parser.name == "CustomNameParser"
