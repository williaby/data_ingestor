"""Integration tests for benchmarking framework with real data."""

import json
from pathlib import Path

import pytest

from data_ingestor.benchmarking.orchestrator import BenchmarkOrchestrator
from data_ingestor.benchmarking.reporter import BenchmarkReporter
from data_ingestor.benchmarking.runner import BenchmarkRunner


@pytest.mark.integration
@pytest.mark.requires_doclaynet
class TestBenchmarkRunner:
    """Integration tests for BenchmarkRunner."""

    def test_runner_initialization_default(self) -> None:
        """Test BenchmarkRunner initialization with defaults."""
        runner = BenchmarkRunner()

        assert runner.workers == 4
        assert runner.batch_size == 32
        assert runner.timeout == 120
        assert runner.settings is not None

    def test_runner_initialization_with_custom_settings(self) -> None:
        """Test BenchmarkRunner initialization with custom settings."""
        runner = BenchmarkRunner(workers=8, batch_size=16, timeout=60)

        assert runner.workers == 8
        assert runner.batch_size == 16
        assert runner.timeout == 60
        assert runner.settings is not None

    def test_runner_has_router_configured(self) -> None:
        """Test runner has parsers available for router configuration."""
        runner = BenchmarkRunner()

        # Settings used to build a router per benchmark run
        assert runner.settings is not None

        # Available parsers can be registered on a per-run router
        assert runner.available_parsers is not None
        assert "pymupdf" in runner.available_parsers

    def test_runner_parallel_configuration(self) -> None:
        """Test runner configures parallel processing correctly."""
        runner = BenchmarkRunner(workers=2, batch_size=10)

        assert runner.workers == 2
        assert runner.batch_size == 10


@pytest.mark.integration
class TestBenchmarkOrchestrator:
    """Integration tests for BenchmarkOrchestrator."""

    def test_orchestrator_initialization_defaults(self) -> None:
        """Test BenchmarkOrchestrator initialization with defaults."""
        # Skip if config file doesn't exist
        config_path = Path("data/benchmarks/config.yaml")
        if not config_path.exists():
            pytest.skip("Benchmark config.yaml not found")

        orchestrator = BenchmarkOrchestrator()

        assert orchestrator.config is not None
        assert orchestrator.config.workers == 4
        assert orchestrator.config.batch_size == 32

    def test_orchestrator_initialization_custom_params(self, tmp_path: Path) -> None:
        """Test orchestrator with custom parameters."""
        # Skip if config file doesn't exist
        config_path = Path("data/benchmarks/config.yaml")
        if not config_path.exists():
            pytest.skip("Benchmark config.yaml not found")

        output_dir = tmp_path / "benchmark_results"

        orchestrator = BenchmarkOrchestrator(
            datasets=["doclaynet"],
            parsers=["pymupdf"],
            workers=2,
            batch_size=16,
            output_dir=str(output_dir),
        )

        assert orchestrator.config.workers == 2
        assert orchestrator.config.batch_size == 16
        assert "doclaynet" in orchestrator.config.datasets
        assert "pymupdf" in orchestrator.config.parsers

    def test_orchestrator_creates_output_directory(self, tmp_path: Path) -> None:
        """Test orchestrator creates output directory."""
        config_path = Path("data/benchmarks/config.yaml")
        if not config_path.exists():
            pytest.skip("Benchmark config.yaml not found")

        output_dir = tmp_path / "new_benchmark_dir"
        assert not output_dir.exists()

        orchestrator = BenchmarkOrchestrator(
            datasets=["doclaynet"],
            output_dir=str(output_dir),
        )

        # Output directory should be created in config
        assert orchestrator.config.output_dir.exists()

    def test_orchestrator_parallel_execution_setup(self, tmp_path: Path) -> None:
        """Test orchestrator parallel execution configuration."""
        config_path = Path("data/benchmarks/config.yaml")
        if not config_path.exists():
            pytest.skip("Benchmark config.yaml not found")

        orchestrator = BenchmarkOrchestrator(
            workers=4,
            output_dir=str(tmp_path / "parallel_results"),
        )

        assert orchestrator.config.workers == 4


@pytest.mark.integration
class TestBenchmarkReporter:
    """Integration tests for BenchmarkReporter with real data."""

    def test_reporter_initialization(self) -> None:
        """Test reporter initialization with proper results structure."""
        # Create proper results structure
        results = {
            "metadata": {
                "timestamp": "2025-11-05T12:00:00Z",
                "datasets": ["doclaynet"],
                "parsers": ["pymupdf"],
            },
            "datasets": {
                "doclaynet": {
                    "pymupdf": {
                        "total_files": 5,
                        "successful": 5,
                        "failed": 0,
                    },
                },
            },
            "overall": {
                "total_files": 5,
                "successful": 5,
            },
        }

        reporter = BenchmarkReporter(results)

        assert reporter.results == results
        assert reporter.metadata == results["metadata"]
        assert reporter.datasets == results["datasets"]

    def test_reporter_generates_html_from_real_results(self, tmp_path: Path) -> None:
        """Test HTML report generation with real benchmark data."""
        # Create proper results structure
        results = {
            "metadata": {
                "timestamp": "2025-11-05T12:00:00Z",
                "benchmark_id": "test-benchmark-001",
            },
            "datasets": {
                "doclaynet": {
                    "pymupdf": {
                        "total_files": 5,
                        "successful": 5,
                    },
                },
            },
            "overall": {},
        }

        reporter = BenchmarkReporter(results)

        # Generate HTML report
        output_file = tmp_path / "benchmark_report.html"
        reporter.generate_html(str(output_file))

        # Verify HTML file was created
        assert output_file.exists()
        assert output_file.stat().st_size > 0

        # Verify HTML contains expected content
        html_content = output_file.read_text()
        assert "benchmark" in html_content.lower()
        assert "2025-11-05" in html_content

    def test_reporter_generates_json_report(self, tmp_path: Path) -> None:
        """Test JSON report generation."""
        results = {
            "metadata": {"timestamp": "2025-11-05T12:00:00Z"},
            "datasets": {},
            "overall": {},
        }

        reporter = BenchmarkReporter(results)

        # Generate JSON report
        output_file = tmp_path / "benchmark_report.json"
        reporter.generate_json(str(output_file))

        # Verify JSON file
        assert output_file.exists()

        # Load and verify content
        with open(output_file) as f:
            report_data = json.load(f)

        assert isinstance(report_data, dict)
        assert "metadata" in report_data

    def test_reporter_generates_csv_report(self, tmp_path: Path) -> None:
        """Test CSV report generation."""
        results = {
            "metadata": {
                "timestamp": "2025-11-05T12:00:00Z",
            },
            "datasets": {
                "doclaynet": {
                    "parsers": {
                        "pymupdf": {
                            "aggregated": {
                                "total_documents": 5,
                                "successful_documents": 5,
                                "failed_documents": 0,
                                "success_rate": 1.0,
                                "avg_processing_time": 0.5,
                            },
                        },
                    },
                },
            },
            "overall": {},
        }

        reporter = BenchmarkReporter(results)

        # Generate CSV report
        output_file = tmp_path / "benchmark_report.csv"
        reporter.generate_csv(str(output_file))

        # Verify CSV file
        assert output_file.exists()
        assert output_file.stat().st_size > 0

        # Verify CSV contains data
        csv_content = output_file.read_text()
        assert len(csv_content) > 0

    def test_reporter_handles_empty_results(self, tmp_path: Path) -> None:
        """Test reporter handles empty results gracefully."""
        results = {
            "metadata": {},
            "datasets": {},
            "overall": {},
        }

        reporter = BenchmarkReporter(results)

        output_file = tmp_path / "empty_report.html"
        reporter.generate_html(str(output_file))

        # Should create file even with no results
        assert output_file.exists()


@pytest.mark.integration
class TestBenchmarkingEdgeCases:
    """Test benchmarking edge cases with real scenarios."""

    def test_runner_with_zero_timeout(self) -> None:
        """Test runner with minimal timeout value."""
        runner = BenchmarkRunner(timeout=1)
        assert runner.timeout == 1

    def test_runner_with_single_worker(self) -> None:
        """Test runner with single worker (no parallelism)."""
        runner = BenchmarkRunner(workers=1)
        assert runner.workers == 1

    def test_reporter_with_minimal_structure(self, tmp_path: Path) -> None:
        """Test reporter with minimal results structure."""
        # Minimal valid structure
        results = {
            "metadata": {},
            "datasets": {},
            "overall": {},
        }

        reporter = BenchmarkReporter(results)
        output_file = tmp_path / "minimal_report.json"
        reporter.generate_json(str(output_file))

        assert output_file.exists()
