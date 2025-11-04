"""Comprehensive tests for custom exception classes."""

import pytest

from data_ingestor.core.exceptions import (
    ChunkingError,
    DataIngestorError,
    ParserError,
    QualityCheckError,
    StorageError,
    UnsupportedFormatError,
)


class TestDataIngestorError:
    """Tests for base DataIngestorError exception."""

    def test_basic_initialization(self) -> None:
        """Test basic exception initialization."""
        error = DataIngestorError("Test error message")
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.details == {}

    def test_initialization_with_details(self) -> None:
        """Test exception with details dictionary."""
        details = {"key": "value", "count": 42}
        error = DataIngestorError("Error with details", details=details)

        assert error.message == "Error with details"
        assert error.details == details
        assert error.details["key"] == "value"
        assert error.details["count"] == 42

    def test_empty_details(self) -> None:
        """Test exception with empty details."""
        error = DataIngestorError("Error", details={})
        assert error.details == {}

    def test_none_details(self) -> None:
        """Test exception with None details defaults to empty dict."""
        error = DataIngestorError("Error", details=None)
        assert error.details == {}

    def test_inheritance_from_exception(self) -> None:
        """Test that DataIngestorError inherits from Exception."""
        error = DataIngestorError("Test")
        assert isinstance(error, Exception)

    def test_can_be_raised_and_caught(self) -> None:
        """Test that exception can be raised and caught."""
        with pytest.raises(DataIngestorError) as exc_info:
            raise DataIngestorError("Test error")

        assert "Test error" in str(exc_info.value)

    def test_string_representation(self) -> None:
        """Test string representation of exception."""
        error = DataIngestorError("Test message")
        assert str(error) == "Test message"

    def test_details_are_mutable(self) -> None:
        """Test that details dict can be modified."""
        error = DataIngestorError("Error", details={"initial": "value"})
        error.details["additional"] = "new_value"
        assert error.details["additional"] == "new_value"


class TestParserError:
    """Tests for ParserError exception."""

    def test_basic_initialization(self) -> None:
        """Test basic ParserError initialization."""
        error = ParserError(message="Parse failed", parser_name="TestParser")

        assert error.message == "Parse failed"
        assert error.parser_name == "TestParser"
        assert error.document_path is None
        assert error.details == {}

    def test_full_initialization(self) -> None:
        """Test ParserError with all parameters."""
        details = {"error_code": "PARSE_001", "line": 42}
        error = ParserError(
            message="Parse failed",
            parser_name="TestParser",
            document_path="/path/to/doc.pdf",
            details=details,
        )

        assert error.message == "Parse failed"
        assert error.parser_name == "TestParser"
        assert error.document_path == "/path/to/doc.pdf"
        assert error.details == details

    def test_inherits_from_data_ingestor_error(self) -> None:
        """Test that ParserError inherits from DataIngestorError."""
        error = ParserError("Error", parser_name="Parser")
        assert isinstance(error, DataIngestorError)
        assert isinstance(error, Exception)

    def test_can_be_caught_as_data_ingestor_error(self) -> None:
        """Test that ParserError can be caught as DataIngestorError."""
        with pytest.raises(DataIngestorError):
            raise ParserError("Error", parser_name="Parser")

    def test_parser_name_attribute(self) -> None:
        """Test parser_name attribute accessibility."""
        error = ParserError("Error", parser_name="CustomParser")
        assert error.parser_name == "CustomParser"

    def test_document_path_attribute(self) -> None:
        """Test document_path attribute."""
        error = ParserError(
            "Error",
            parser_name="Parser",
            document_path="/docs/test.pdf",
        )
        assert error.document_path == "/docs/test.pdf"


class TestUnsupportedFormatError:
    """Tests for UnsupportedFormatError exception."""

    def test_basic_initialization(self) -> None:
        """Test basic UnsupportedFormatError initialization."""
        error = UnsupportedFormatError(format_detected="xyz")

        assert "xyz" in error.message
        assert error.format_detected == "xyz"
        assert error.details["file_extension"] is None
        assert error.details["mime_type"] is None

    def test_initialization_with_extension(self) -> None:
        """Test with file extension."""
        error = UnsupportedFormatError(
            format_detected="unknown",
            file_extension=".xyz",
        )

        assert error.format_detected == "unknown"
        assert error.details["file_extension"] == ".xyz"

    def test_initialization_with_mime_type(self) -> None:
        """Test with MIME type."""
        error = UnsupportedFormatError(
            format_detected="unknown",
            mime_type="application/unknown",
        )

        assert error.details["mime_type"] == "application/unknown"

    def test_full_initialization(self) -> None:
        """Test with all parameters."""
        error = UnsupportedFormatError(
            format_detected="xyz",
            file_extension=".xyz",
            mime_type="application/xyz",
        )

        assert error.format_detected == "xyz"
        assert error.details["file_extension"] == ".xyz"
        assert error.details["mime_type"] == "application/xyz"
        assert "xyz" in error.message

    def test_none_format_detected(self) -> None:
        """Test with None format_detected."""
        error = UnsupportedFormatError(format_detected=None)
        assert "unknown" in error.message
        assert error.format_detected is None

    def test_inherits_from_data_ingestor_error(self) -> None:
        """Test inheritance."""
        error = UnsupportedFormatError("test")
        assert isinstance(error, DataIngestorError)

    def test_message_format(self) -> None:
        """Test that message is properly formatted."""
        error = UnsupportedFormatError(format_detected="custom_format")
        assert "Unsupported document format" in error.message
        assert "custom_format" in error.message


class TestQualityCheckError:
    """Tests for QualityCheckError exception."""

    def test_basic_initialization(self) -> None:
        """Test basic QualityCheckError initialization."""
        error = QualityCheckError(
            quality_score=0.65,
            threshold=0.70,
        )

        assert error.quality_score == 0.65
        assert error.threshold == 0.70
        assert error.document_id is None
        assert "0.65" in error.message
        assert "0.7" in error.message

    def test_full_initialization(self) -> None:
        """Test with all parameters."""
        failed_checks = ["text_extraction", "table_accuracy"]
        error = QualityCheckError(
            quality_score=0.65,
            threshold=0.80,
            document_id="doc-123",
            failed_checks=failed_checks,
        )

        assert error.quality_score == 0.65
        assert error.threshold == 0.80
        assert error.document_id == "doc-123"
        assert error.details["failed_checks"] == failed_checks
        assert error.details["quality_score"] == 0.65
        assert error.details["threshold"] == 0.80

    def test_failed_checks_in_details(self) -> None:
        """Test that failed checks are stored in details."""
        failed_checks = ["check1", "check2", "check3"]
        error = QualityCheckError(
            quality_score=0.5,
            threshold=0.7,
            failed_checks=failed_checks,
        )

        assert error.details["failed_checks"] == failed_checks

    def test_empty_failed_checks(self) -> None:
        """Test with no failed checks."""
        error = QualityCheckError(quality_score=0.65, threshold=0.70)
        assert error.details["failed_checks"] == []

    def test_none_failed_checks(self) -> None:
        """Test with None failed_checks defaults to empty list."""
        error = QualityCheckError(
            quality_score=0.65,
            threshold=0.70,
            failed_checks=None,
        )
        assert error.details["failed_checks"] == []

    def test_inherits_from_data_ingestor_error(self) -> None:
        """Test inheritance."""
        error = QualityCheckError(quality_score=0.5, threshold=0.7)
        assert isinstance(error, DataIngestorError)

    def test_quality_score_attribute(self) -> None:
        """Test quality_score attribute."""
        error = QualityCheckError(quality_score=0.55, threshold=0.70)
        assert error.quality_score == 0.55

    def test_threshold_attribute(self) -> None:
        """Test threshold attribute."""
        error = QualityCheckError(quality_score=0.65, threshold=0.80)
        assert error.threshold == 0.80

    def test_document_id_attribute(self) -> None:
        """Test document_id attribute."""
        error = QualityCheckError(
            quality_score=0.65,
            threshold=0.70,
            document_id="test-doc-456",
        )
        assert error.document_id == "test-doc-456"


class TestStorageError:
    """Tests for StorageError exception."""

    def test_basic_initialization(self) -> None:
        """Test StorageError initialization."""
        error = StorageError("Storage operation failed")
        assert error.message == "Storage operation failed"
        assert error.details == {}

    def test_initialization_with_details(self) -> None:
        """Test StorageError with details."""
        details = {"operation": "write", "path": "/data/file"}
        error = StorageError("Write failed", details=details)

        assert error.message == "Write failed"
        assert error.details == details

    def test_inherits_from_data_ingestor_error(self) -> None:
        """Test inheritance."""
        error = StorageError("Error")
        assert isinstance(error, DataIngestorError)

    def test_can_be_raised(self) -> None:
        """Test that StorageError can be raised."""
        with pytest.raises(StorageError) as exc_info:
            raise StorageError("Storage error occurred")

        assert "Storage error occurred" in str(exc_info.value)


class TestChunkingError:
    """Tests for ChunkingError exception."""

    def test_basic_initialization(self) -> None:
        """Test ChunkingError initialization."""
        error = ChunkingError("Chunking failed")
        assert error.message == "Chunking failed"
        assert error.details == {}

    def test_initialization_with_details(self) -> None:
        """Test ChunkingError with details."""
        details = {"chunk_size": 1000, "overlap": 200}
        error = ChunkingError("Invalid chunk size", details=details)

        assert error.message == "Invalid chunk size"
        assert error.details == details

    def test_inherits_from_data_ingestor_error(self) -> None:
        """Test inheritance."""
        error = ChunkingError("Error")
        assert isinstance(error, DataIngestorError)

    def test_can_be_raised(self) -> None:
        """Test that ChunkingError can be raised."""
        with pytest.raises(ChunkingError) as exc_info:
            raise ChunkingError("Chunking error occurred")

        assert "Chunking error occurred" in str(exc_info.value)


class TestExceptionHierarchy:
    """Tests for exception inheritance hierarchy."""

    def test_all_exceptions_inherit_from_base(self) -> None:
        """Test that all custom exceptions inherit from DataIngestorError."""
        exceptions = [
            ParserError("msg", parser_name="p"),
            UnsupportedFormatError("fmt"),
            QualityCheckError(0.5, 0.7),
            StorageError("msg"),
            ChunkingError("msg"),
        ]

        for error in exceptions:
            assert isinstance(error, DataIngestorError)
            assert isinstance(error, Exception)

    def test_catching_base_exception(self) -> None:
        """Test catching all custom exceptions with base class."""
        exceptions = [
            ParserError("msg", parser_name="p"),
            UnsupportedFormatError("fmt"),
            QualityCheckError(0.5, 0.7),
            StorageError("msg"),
            ChunkingError("msg"),
        ]

        for error in exceptions:
            with pytest.raises(DataIngestorError):
                raise error


class TestExceptionDetails:
    """Tests for exception details handling."""

    def test_details_with_complex_types(self) -> None:
        """Test details with various data types."""
        details = {
            "string": "value",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
        }
        error = DataIngestorError("Error", details=details)
        assert error.details == details

    def test_details_modification(self) -> None:
        """Test that details can be modified after creation."""
        error = DataIngestorError("Error", details={"initial": "value"})
        error.details["new_key"] = "new_value"

        assert error.details["initial"] == "value"
        assert error.details["new_key"] == "new_value"

    def test_parser_error_preserves_base_details(self) -> None:
        """Test that ParserError preserves base class details."""
        details = {"custom": "data"}
        error = ParserError("msg", parser_name="p", details=details)

        assert error.details["custom"] == "data"


class TestExceptionMessages:
    """Tests for exception message formatting."""

    def test_parser_error_message(self) -> None:
        """Test ParserError message."""
        error = ParserError("Failed to parse", parser_name="PyMuPDF")
        assert "Failed to parse" in str(error)

    def test_unsupported_format_message(self) -> None:
        """Test UnsupportedFormatError message format."""
        error = UnsupportedFormatError("xyz", file_extension=".xyz")
        message = str(error)

        assert "Unsupported document format" in message
        assert "xyz" in message

    def test_quality_check_error_message(self) -> None:
        """Test QualityCheckError message format."""
        error = QualityCheckError(0.65, 0.80)
        message = str(error)

        assert "Quality check failed" in message
        assert "0.65" in message
        assert "0.8" in message


class TestExceptionUsagePatterns:
    """Tests for common exception usage patterns."""

    def test_reraise_with_context(self) -> None:
        """Test raising exception with context."""
        with pytest.raises(DataIngestorError) as exc_info:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise DataIngestorError("Wrapped error") from e

        assert exc_info.value.__cause__ is not None

    def test_exception_in_context_manager(self) -> None:
        """Test using exceptions in context managers."""
        caught = False
        try:
            with pytest.raises(ParserError):
                raise ParserError("Test", parser_name="Test")
            caught = True
        except Exception:
            pass

        assert caught

    def test_multiple_exception_types(self) -> None:
        """Test catching multiple exception types."""
        errors = [
            ParserError("msg", parser_name="p"),
            StorageError("msg"),
            ChunkingError("msg"),
        ]

        for error in errors:
            with pytest.raises((ParserError, StorageError, ChunkingError)):
                raise error
