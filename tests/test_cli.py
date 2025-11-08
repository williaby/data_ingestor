"""Comprehensive tests for CLI module."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

from data_ingestor.cli.main import _display_preview, cli, health, process, setup_logging
from data_ingestor.core.models import Document, DocumentElement, DocumentFormat, ElementType, ParserResult


@pytest.fixture
def runner():
    """Create CLI runner fixture."""
    return CliRunner()


@pytest.fixture
def mock_document():
    """Create mock document for testing."""
    elements = [
        DocumentElement(element_type=ElementType.TITLE, content="Test Title"),
        DocumentElement(element_type=ElementType.PARAGRAPH, content="This is a test paragraph" * 10),
    ]
    doc = Document(
        source_path=None,
        format=DocumentFormat.PDF,
        elements=elements,
    )
    return doc


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging_info_level(self) -> None:
        """Test logging setup with INFO level."""
        setup_logging(debug=False)
        # Logging is configured, no assertion needed

    def test_setup_logging_debug_level(self) -> None:
        """Test logging setup with DEBUG level."""
        setup_logging(debug=True)
        # Logging is configured, no assertion needed


class TestCLIGroup:
    """Tests for CLI group command."""

    def test_cli_help(self, runner: CliRunner) -> None:
        """Test CLI help message."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Data Ingestor" in result.output

    def test_cli_debug_flag(self, runner: CliRunner) -> None:
        """Test CLI with debug flag."""
        result = runner.invoke(cli, ["--debug", "--help"])
        assert result.exit_code == 0


class TestProcessCommand:
    """Tests for process command."""

    @patch("data_ingestor.cli.main.DocumentRouter")
    @patch("data_ingestor.cli.main.MarkerParser")
    @patch("data_ingestor.cli.main.PyMuPDF4LLMParser")
    @patch("data_ingestor.cli.main.PyMuPDFParser")
    def test_process_pdf_basic(
        self,
        mock_pymupdf,
        mock_pymupdf4llm,
        mock_marker,
        mock_router,
        runner: CliRunner,
        temp_test_file: Path,
    ) -> None:
        """Test basic PDF processing."""
        # Setup mocks
        mock_router_instance = MagicMock()
        mock_router.return_value = mock_router_instance

        # Create mock result
        elements = [
            DocumentElement(element_type=ElementType.TITLE, content="Test"),
        ]
        doc = Document(
            source_path=str(temp_test_file),
            format=DocumentFormat.PDF,
            elements=elements,
        )
        result = ParserResult(
            success=True,
            elements=elements,
            parser_name="TestParser",
            processing_time=1.0,
        )
        mock_router_instance.process_document.return_value = (doc, result)

        # Run command
        cmd_result = runner.invoke(
            cli,
            ["process", str(temp_test_file)],
        )

        assert cmd_result.exit_code == 0
        assert "Processing document" in cmd_result.output

    @patch("data_ingestor.cli.main.DocumentRouter")
    @patch("data_ingestor.cli.main.MarkerParser")
    @patch("data_ingestor.cli.main.PyMuPDF4LLMParser")
    @patch("data_ingestor.cli.main.PyMuPDFParser")
    def test_process_with_json_output(
        self,
        mock_pymupdf,
        mock_pymupdf4llm,
        mock_marker,
        mock_router,
        runner: CliRunner,
        temp_test_file: Path,
        tmp_path: Path,
    ) -> None:
        """Test processing with JSON output."""
        # Setup mocks
        mock_router_instance = MagicMock()
        mock_router.return_value = mock_router_instance

        elements = [DocumentElement(element_type=ElementType.TITLE, content="Test")]
        doc = Document(
            source_path=str(temp_test_file),
            format=DocumentFormat.PDF,
            elements=elements,
        )
        result = ParserResult(
            success=True,
            elements=elements,
            parser_name="TestParser",
            processing_time=1.0,
        )
        mock_router_instance.process_document.return_value = (doc, result)

        output_file = tmp_path / "output.json"

        # Run command
        cmd_result = runner.invoke(
            cli,
            ["process", str(temp_test_file), "--output", str(output_file), "--format", "json"],
        )

        assert cmd_result.exit_code == 0

    @patch("data_ingestor.cli.main.DocumentRouter")
    @patch("data_ingestor.cli.main.MarkerParser")
    @patch("data_ingestor.cli.main.PyMuPDF4LLMParser")
    @patch("data_ingestor.cli.main.PyMuPDFParser")
    def test_process_with_markdown_output(
        self,
        mock_pymupdf,
        mock_pymupdf4llm,
        mock_marker,
        mock_router,
        runner: CliRunner,
        temp_test_file: Path,
        tmp_path: Path,
    ) -> None:
        """Test processing with Markdown output."""
        # Setup mocks
        mock_router_instance = MagicMock()
        mock_router.return_value = mock_router_instance

        elements = [DocumentElement(element_type=ElementType.TITLE, content="Test")]
        doc = Document(
            source_path=str(temp_test_file),
            format=DocumentFormat.PDF,
            elements=elements,
        )
        result = ParserResult(
            success=True,
            elements=elements,
            parser_name="TestParser",
            processing_time=1.0,
        )
        mock_router_instance.process_document.return_value = (doc, result)

        output_file = tmp_path / "output.md"

        # Run command
        cmd_result = runner.invoke(
            cli,
            ["process", str(temp_test_file), "--output", str(output_file), "--format", "markdown"],
        )

        assert cmd_result.exit_code == 0

    @patch("data_ingestor.cli.main.DocumentRouter")
    @patch("data_ingestor.cli.main.MarkerParser")
    @patch("data_ingestor.cli.main.PyMuPDF4LLMParser")
    @patch("data_ingestor.cli.main.PyMuPDFParser")
    def test_process_with_both_output(
        self,
        mock_pymupdf,
        mock_pymupdf4llm,
        mock_marker,
        mock_router,
        runner: CliRunner,
        temp_test_file: Path,
        tmp_path: Path,
    ) -> None:
        """Test processing with both JSON and Markdown output."""
        # Setup mocks
        mock_router_instance = MagicMock()
        mock_router.return_value = mock_router_instance

        elements = [DocumentElement(element_type=ElementType.TITLE, content="Test")]
        doc = Document(
            source_path=str(temp_test_file),
            format=DocumentFormat.PDF,
            elements=elements,
        )
        result = ParserResult(
            success=True,
            elements=elements,
            parser_name="TestParser",
            processing_time=1.0,
        )
        mock_router_instance.process_document.return_value = (doc, result)

        output_file = tmp_path / "output"

        # Run command
        cmd_result = runner.invoke(
            cli,
            ["process", str(temp_test_file), "--output", str(output_file), "--format", "both"],
        )

        assert cmd_result.exit_code == 0

    @patch("data_ingestor.cli.main.DocumentRouter")
    @patch("data_ingestor.cli.main.MarkerParser")
    @patch("data_ingestor.cli.main.PyMuPDF4LLMParser")
    @patch("data_ingestor.cli.main.PyMuPDFParser")
    def test_process_with_chunking(
        self,
        mock_pymupdf,
        mock_pymupdf4llm,
        mock_marker,
        mock_router,
        runner: CliRunner,
        temp_test_file: Path,
    ) -> None:
        """Test processing with chunking enabled."""
        # Setup mocks
        mock_router_instance = MagicMock()
        mock_router.return_value = mock_router_instance

        elements = [
            DocumentElement(element_type=ElementType.TITLE, content="Test"),
            DocumentElement(element_type=ElementType.PARAGRAPH, content="Test paragraph" * 50),
        ]
        doc = Document(
            source_path=str(temp_test_file),
            format=DocumentFormat.PDF,
            elements=elements,
        )
        result = ParserResult(
            success=True,
            elements=elements,
            parser_name="TestParser",
            processing_time=1.0,
        )
        mock_router_instance.process_document.return_value = (doc, result)

        # Run command with chunking
        cmd_result = runner.invoke(
            cli,
            [
                "process",
                str(temp_test_file),
                "--chunk-size",
                "500",
                "--chunk-overlap",
                "100",
            ],
        )

        assert cmd_result.exit_code == 0
        assert "Chunking document" in cmd_result.output

    @patch("data_ingestor.cli.main.DocumentRouter")
    @patch("data_ingestor.cli.main.MarkerParser")
    @patch("data_ingestor.cli.main.PyMuPDF4LLMParser")
    @patch("data_ingestor.cli.main.PyMuPDFParser")
    def test_process_with_by_title_strategy(
        self,
        mock_pymupdf,
        mock_pymupdf4llm,
        mock_marker,
        mock_router,
        runner: CliRunner,
        temp_test_file: Path,
    ) -> None:
        """Test processing with by_title chunking strategy."""
        # Setup mocks
        mock_router_instance = MagicMock()
        mock_router.return_value = mock_router_instance

        elements = [
            DocumentElement(element_type=ElementType.TITLE, content="Test"),
            DocumentElement(element_type=ElementType.PARAGRAPH, content="Test paragraph" * 50),
        ]
        doc = Document(
            source_path=str(temp_test_file),
            format=DocumentFormat.PDF,
            elements=elements,
        )
        result = ParserResult(
            success=True,
            elements=elements,
            parser_name="TestParser",
            processing_time=1.0,
        )
        mock_router_instance.process_document.return_value = (doc, result)

        # Run command with by_title strategy
        cmd_result = runner.invoke(
            cli,
            [
                "process",
                str(temp_test_file),
                "--chunking-strategy",
                "by_title",
                "--combine-under",
                "100",
            ],
        )

        assert cmd_result.exit_code == 0
        assert "by_title strategy" in cmd_result.output

    @patch("data_ingestor.cli.main.DocumentRouter")
    @patch("data_ingestor.cli.main.MarkerParser")
    @patch("data_ingestor.cli.main.PyMuPDF4LLMParser")
    @patch("data_ingestor.cli.main.PyMuPDFParser")
    def test_process_parsing_failure(
        self,
        mock_pymupdf,
        mock_pymupdf4llm,
        mock_marker,
        mock_router,
        runner: CliRunner,
        temp_test_file: Path,
    ) -> None:
        """Test processing when parsing fails."""
        # Setup mocks
        mock_router_instance = MagicMock()
        mock_router.return_value = mock_router_instance

        doc = Document(
            source_path=str(temp_test_file),
            format=DocumentFormat.PDF,
        )
        result = ParserResult(
            success=False,
            parser_name="TestParser",
            processing_time=1.0,
            error_message="Test error",
        )
        mock_router_instance.process_document.return_value = (doc, result)

        # Run command
        cmd_result = runner.invoke(
            cli,
            ["process", str(temp_test_file)],
        )

        assert cmd_result.exit_code == 1
        assert "Error" in cmd_result.output

    @patch("data_ingestor.cli.main.DocumentRouter")
    @patch("data_ingestor.cli.main.MarkerParser")
    @patch("data_ingestor.cli.main.PyMuPDF4LLMParser")
    @patch("data_ingestor.cli.main.PyMuPDFParser")
    def test_process_exception_handling(
        self,
        mock_pymupdf,
        mock_pymupdf4llm,
        mock_marker,
        mock_router,
        runner: CliRunner,
        temp_test_file: Path,
    ) -> None:
        """Test process command exception handling."""
        # Setup mocks to raise exception
        mock_router_instance = MagicMock()
        mock_router.return_value = mock_router_instance
        mock_router_instance.process_document.side_effect = Exception("Test exception")

        # Run command
        cmd_result = runner.invoke(
            cli,
            ["process", str(temp_test_file)],
        )

        assert cmd_result.exit_code == 1
        assert "Error" in cmd_result.output

    @patch("data_ingestor.cli.main.DocumentRouter")
    @patch("data_ingestor.cli.main.MarkerParser")
    @patch("data_ingestor.cli.main.PyMuPDF4LLMParser")
    @patch("data_ingestor.cli.main.PyMuPDFParser")
    def test_process_with_include_chunks_flag(
        self,
        mock_pymupdf,
        mock_pymupdf4llm,
        mock_marker,
        mock_router,
        runner: CliRunner,
        temp_test_file: Path,
        tmp_path: Path,
    ) -> None:
        """Test processing with include-chunks flag."""
        # Setup mocks
        mock_router_instance = MagicMock()
        mock_router.return_value = mock_router_instance

        elements = [
            DocumentElement(element_type=ElementType.TITLE, content="Test"),
            DocumentElement(element_type=ElementType.PARAGRAPH, content="Test paragraph" * 50),
        ]
        doc = Document(
            source_path=str(temp_test_file),
            format=DocumentFormat.PDF,
            elements=elements,
        )
        result = ParserResult(
            success=True,
            elements=elements,
            parser_name="TestParser",
            processing_time=1.0,
        )
        mock_router_instance.process_document.return_value = (doc, result)

        output_file = tmp_path / "output.md"

        # Run command with include-chunks
        cmd_result = runner.invoke(
            cli,
            [
                "process",
                str(temp_test_file),
                "--format",
                "markdown",
                "--output",
                str(output_file),
                "--include-chunks",
            ],
        )

        assert cmd_result.exit_code == 0


class TestHealthCommand:
    """Tests for health command."""

    @patch("data_ingestor.cli.main.DocumentRouter")
    @patch("data_ingestor.cli.main.MarkerParser")
    @patch("data_ingestor.cli.main.PyMuPDF4LLMParser")
    @patch("data_ingestor.cli.main.PyMuPDFParser")
    def test_health_check_all_healthy(
        self,
        mock_pymupdf,
        mock_pymupdf4llm,
        mock_marker,
        mock_router,
        runner: CliRunner,
    ) -> None:
        """Test health check when all parsers are healthy."""
        # Setup mocks
        mock_router_instance = MagicMock()
        mock_router.return_value = mock_router_instance
        mock_router_instance.parser_registry.health_check.return_value = {
            "PDF": [
                {"name": "MarkerParser", "healthy": True},
                {"name": "PyMuPDF4LLMParser", "healthy": True},
                {"name": "PyMuPDFParser", "healthy": True},
            ],
        }

        # Run command
        result = runner.invoke(cli, ["health"])

        assert result.exit_code == 0
        assert "Parser Health Status" in result.output
        assert "Healthy" in result.output

    @patch("data_ingestor.cli.main.DocumentRouter")
    @patch("data_ingestor.cli.main.MarkerParser")
    @patch("data_ingestor.cli.main.PyMuPDF4LLMParser")
    @patch("data_ingestor.cli.main.PyMuPDFParser")
    def test_health_check_with_unhealthy_parser(
        self,
        mock_pymupdf,
        mock_pymupdf4llm,
        mock_marker,
        mock_router,
        runner: CliRunner,
    ) -> None:
        """Test health check with one unhealthy parser."""
        # Setup mocks
        mock_router_instance = MagicMock()
        mock_router.return_value = mock_router_instance
        mock_router_instance.parser_registry.health_check.return_value = {
            "PDF": [
                {"name": "MarkerParser", "healthy": False, "error": "Test error"},
                {"name": "PyMuPDF4LLMParser", "healthy": True},
                {"name": "PyMuPDFParser", "healthy": True},
            ],
        }

        # Run command
        result = runner.invoke(cli, ["health"])

        assert result.exit_code == 0
        assert "Unhealthy" in result.output
        assert "Test error" in result.output


class TestDisplayPreview:
    """Tests for _display_preview helper function."""

    def test_display_preview_short_document(self, mock_document: Document) -> None:
        """Test preview display for short document."""
        from rich.console import Console
        console = Console()
        _display_preview(mock_document, console)
        # Function should execute without errors

    def test_display_preview_long_document(self) -> None:
        """Test preview display for long document."""
        from rich.console import Console
        console = Console()
        elements = [
            DocumentElement(element_type=ElementType.PARAGRAPH, content=f"Paragraph {i}")
            for i in range(20)
        ]
        doc = Document(
            source_path=None,
            format=DocumentFormat.PDF,
            elements=elements,
        )

        _display_preview(doc, console)
        # Should handle > 10 elements

    def test_display_preview_with_chunks(self, mock_document: Document) -> None:
        """Test preview display with chunks."""
        from rich.console import Console
        from data_ingestor.core.models import Chunk

        console = Console()
        chunks = [
            Chunk(content=f"Chunk {i} content " * 50, metadata={}, token_count=100)
            for i in range(5)
        ]
        mock_document.chunks = chunks

        _display_preview(mock_document, console)
        # Should display chunk preview
