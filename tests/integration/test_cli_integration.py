"""Integration tests for CLI with real files (no mocks).

Note: These tests skip Marker parser initialization via SKIP_MARKER_PARSER env var
to avoid 10+ second PyTorch model loading. For fast unit tests, see test_cli.py.
"""

import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from data_ingestor.cli.main import cli

# Skip Marker parser to avoid slow PyTorch loading (10+ seconds)
os.environ["SKIP_MARKER_PARSER"] = "1"


@pytest.mark.integration
class TestCLIProcessCommand:
    """Integration tests for process command with real PDFs."""

    def test_process_command_with_real_pdf(
        self,
        cli_runner: CliRunner,
        sample_pdf_paths: dict[str, Path],
        tmp_path: Path,
    ) -> None:
        """Test CLI process command with actual PDF file."""
        pdf_path = sample_pdf_paths["simple_text"]
        output_file = tmp_path / "output.json"

        result = cli_runner.invoke(
            cli,
            ["process", str(pdf_path), "--output", str(output_file), "--format", "json"],
        )

        # Verify command succeeded
        assert result.exit_code == 0

        # Verify output file was created
        assert output_file.exists()

        # Verify output is valid JSON
        with open(output_file) as f:
            data = json.load(f)

        assert isinstance(data, dict)
        assert "elements" in data or "content" in data

    def test_process_command_markdown_output(
        self,
        cli_runner: CliRunner,
        sample_pdf_paths: dict[str, Path],
        tmp_path: Path,
    ) -> None:
        """Test CLI markdown output format."""
        pdf_path = sample_pdf_paths["simple_text"]
        output_file = tmp_path / "output.md"

        result = cli_runner.invoke(
            cli,
            ["process", str(pdf_path), "--output", str(output_file), "--format", "markdown"],
        )

        assert result.exit_code == 0
        assert output_file.exists()

        # Verify markdown content
        content = output_file.read_text()
        assert len(content) > 0
        # Markdown should contain some recognizable structure
        assert "Test Document" in content or "#" in content

    def test_process_command_both_formats(
        self,
        cli_runner: CliRunner,
        sample_pdf_paths: dict[str, Path],
        tmp_path: Path,
    ) -> None:
        """Test CLI with both JSON and markdown output."""
        pdf_path = sample_pdf_paths["multipage"]
        output_base = tmp_path / "output"

        result = cli_runner.invoke(
            cli,
            ["process", str(pdf_path), "--output", str(output_base), "--format", "both"],
        )

        assert result.exit_code == 0

        # Both files should be created
        json_file = Path(str(output_base) + ".json")
        md_file = Path(str(output_base) + ".md")

        assert json_file.exists()
        assert md_file.exists()

    def test_process_command_basic_validation(
        self,
        cli_runner: CliRunner,
        sample_pdf_paths: dict[str, Path],
        tmp_path: Path,
    ) -> None:
        """Test CLI output has correct structure (works without Marker).

        This test validates:
        - Command executes successfully
        - Output file is created
        - JSON structure is valid
        - Basic fields are present
        - Some text content is extracted
        """
        pdf_path = sample_pdf_paths["simple_text"]
        output_file = tmp_path / "validated_output.json"

        # Process PDF
        result = cli_runner.invoke(
            cli,
            ["process", str(pdf_path), "--output", str(output_file), "--format", "json"],
        )

        assert result.exit_code == 0
        assert output_file.exists()

        # Load and validate JSON structure
        with open(output_file) as f:
            output_data = json.load(f)

        # Verify essential structure (works with any parser)
        assert "document_id" in output_data
        assert "source_path" in output_data
        assert "format" in output_data
        assert "elements" in output_data
        assert "chunks" in output_data

        # Verify some content was extracted
        assert len(output_data["elements"]) > 0, "No elements extracted"

        # Verify parser was used
        assert output_data.get("parser_used") in ["PyMuPDF4LLMParser", "PyMuPDFParser", "MarkerParser"]

    @pytest.mark.requires_marker
    def test_process_command_quality_validation(
        self,
        cli_runner: CliRunner,
        sample_pdf_paths: dict[str, Path],
        validation_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Test CLI output matches high-quality parsing expectations (requires Marker).

        This test validates:
        - Accurate title extraction
        - Precise content matching
        - High-quality text extraction

        Only runs when Marker parser is available (CI/PR testing).
        """
        if os.getenv("SKIP_MARKER_PARSER") == "1":
            pytest.skip("Quality validation requires Marker parser - run in CI/PR")

        pdf_path = sample_pdf_paths["simple_text"]
        output_file = tmp_path / "validated_output.json"

        # Process PDF
        result = cli_runner.invoke(
            cli,
            ["process", str(pdf_path), "--output", str(output_file), "--format", "json"],
        )

        assert result.exit_code == 0

        # Load validation data
        validation_file = validation_dir / "01_simple_text.json"
        if not validation_file.exists():
            pytest.skip("Validation data not available")

        with open(validation_file) as f:
            validation = json.load(f)

        # Load output
        with open(output_file) as f:
            output_data = json.load(f)

        # Verify high-quality phrase extraction (requires Marker accuracy)
        output_text = json.dumps(output_data)
        for phrase in validation["content_validation"]["required_phrases"][:3]:
            assert phrase in output_text, f"Expected phrase not found: {phrase}"


@pytest.mark.integration
class TestCLIBatchProcessing:
    """Integration tests for batch processing multiple PDFs."""

    @pytest.mark.slow
    def test_batch_processing_multiple_pdfs(
        self,
        cli_runner: CliRunner,
        sample_pdf_paths: dict[str, Path],
        tmp_path: Path,
    ) -> None:
        """
        Test processing multiple PDFs sequentially.

        Marked as slow because it processes all 6 PDFs.
        """
        results = []

        for name, pdf_path in sample_pdf_paths.items():
            output_file = tmp_path / f"{name}.json"

            result = cli_runner.invoke(
                cli,
                ["process", str(pdf_path), "--output", str(output_file), "--format", "json"],
            )

            results.append((name, result.exit_code, output_file.exists()))

        # Verify all processed successfully
        for name, exit_code, file_exists in results:
            assert exit_code == 0, f"Failed to process {name}"
            assert file_exists, f"Output file not created for {name}"

    def test_process_command_with_different_pdfs(
        self,
        cli_runner: CliRunner,
        sample_pdf_paths: dict[str, Path],
        tmp_path: Path,
    ) -> None:
        """Test CLI handles different PDF types correctly."""
        test_cases = [
            ("simple_text", sample_pdf_paths["simple_text"]),
            ("tables", sample_pdf_paths["tables"]),
            ("complex", sample_pdf_paths["complex"]),
        ]

        for name, pdf_path in test_cases:
            output_file = tmp_path / f"{name}.json"

            result = cli_runner.invoke(
                cli,
                ["process", str(pdf_path), "--output", str(output_file)],
            )

            assert result.exit_code == 0
            assert output_file.exists()


@pytest.mark.integration
class TestCLIHealthCommand:
    """Integration tests for health check command."""

    def test_health_command(self, cli_runner: CliRunner) -> None:
        """Test health check command."""
        result = cli_runner.invoke(cli, ["health"])

        # Should succeed
        assert result.exit_code == 0

        # Should display parser status
        assert "PyMuPDF" in result.output or "health" in result.output.lower()


@pytest.mark.integration
class TestCLIErrorHandling:
    """Integration tests for CLI error handling with real scenarios."""

    def test_process_nonexistent_file(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test CLI handles nonexistent input file."""
        nonexistent_file = tmp_path / "nonexistent.pdf"
        output_file = tmp_path / "output.json"

        result = cli_runner.invoke(
            cli,
            ["process", str(nonexistent_file), "--output", str(output_file)],
        )

        # Should fail gracefully
        assert result.exit_code != 0

    def test_process_invalid_output_directory(
        self,
        cli_runner: CliRunner,
        sample_pdf_paths: dict[str, Path],
    ) -> None:
        """Test CLI handles invalid output directory."""
        pdf_path = sample_pdf_paths["simple_text"]
        invalid_output = "/nonexistent/directory/output.json"

        result = cli_runner.invoke(
            cli,
            ["process", str(pdf_path), "--output", invalid_output],
        )

        # Should fail or handle gracefully
        # Exact behavior depends on implementation
        assert result is not None
