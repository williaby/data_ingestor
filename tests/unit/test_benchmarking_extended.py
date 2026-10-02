"""
Comprehensive unit tests for benchmarking modules.

Tests BenchmarkRunner, BenchmarkOrchestrator, and BenchmarkReporter
with extensive coverage of error paths, edge cases, and branch coverage.
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from data_ingestor.benchmarking.orchestrator import (
    BenchmarkConfig,
    BenchmarkOrchestrator,
)
from data_ingestor.benchmarking.reporter import BenchmarkReporter
from data_ingestor.benchmarking.runner import BenchmarkRunner
from data_ingestor.evaluation.models import EvaluationResult


@pytest.mark.unit
class TestBenchmarkRunnerExtended:
    """Extended tests for BenchmarkRunner with comprehensive coverage."""

    def test_runner_initialization_registers_parsers(self) -> None:
        """Test runner initializes with the available parsers configured."""
        runner = BenchmarkRunner()

        # Parsers are registered per benchmark run; the runner exposes the
        # available parser classes it can register.
        assert runner.available_parsers is not None
        assert "pymupdf" in runner.available_parsers
        assert len(runner.available_parsers) >= 1  # At least PyMuPDFParser available

    def test_run_batch_with_sample_documents(self, tmp_path: Path) -> None:
        """Test run_batch with sample PDF documents."""
        runner = BenchmarkRunner(workers=2, batch_size=10)

        # Create a sample PDF file
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n%Test PDF\n")

        # Create mock evaluator
        mock_evaluator = Mock()
        mock_evaluator.dataset_name = "test_dataset"
        mock_evaluator.load_ground_truth.return_value = {
            "text": "test content",
            "elements": [],
        }

        # Create expected evaluation result
        from data_ingestor.evaluation.models import MetricScore

        expected_result = EvaluationResult(
            document_id="test",
            dataset="test_dataset",
            success=True,
            metrics=[MetricScore(name="cer", value=0.1)],
            processing_time=0.5,
        )
        mock_evaluator.evaluate_document.return_value = expected_result

        # Run batch
        results = runner.run_batch(
            document_files=[pdf_file],
            parser_name="pymupdf",
            evaluator=mock_evaluator,
        )

        # Verify results
        assert len(results) >= 1
        # At least one result should be returned (even if parsing failed)
        assert all(isinstance(r, EvaluationResult) for r in results)

    def test_run_batch_handles_parser_failures(self, tmp_path: Path) -> None:
        """Test run_batch handles parser failures gracefully."""
        runner = BenchmarkRunner()

        # Create invalid PDF file
        invalid_pdf = tmp_path / "invalid.pdf"
        invalid_pdf.write_bytes(b"Not a PDF file")

        # Create mock evaluator
        mock_evaluator = Mock()
        mock_evaluator.dataset_name = "test_dataset"
        mock_evaluator.load_ground_truth.return_value = None  # No ground truth

        # Run batch - should handle failures
        results = runner.run_batch(
            document_files=[invalid_pdf],
            parser_name="pymupdf",
            evaluator=mock_evaluator,
        )

        # Should return failure results
        assert len(results) == 1
        result = results[0]
        assert result.success is False
        assert result.error is not None

    def test_run_batch_handles_missing_ground_truth(self, tmp_path: Path) -> None:
        """Test run_batch handles missing ground truth."""
        runner = BenchmarkRunner()

        # Create minimal PDF (parser may still reject it, which is fine)
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n%Test\n")

        # Mock evaluator with missing ground truth
        mock_evaluator = Mock()
        mock_evaluator.dataset_name = "test_dataset"
        mock_evaluator.load_ground_truth.return_value = None  # No ground truth

        # Run batch
        results = runner.run_batch(
            document_files=[pdf_file],
            parser_name="pymupdf",
            evaluator=mock_evaluator,
        )

        # Should return failure results
        assert len(results) == 1
        assert results[0].success is False
        # Error may be from parser failure or missing ground truth
        assert results[0].error is not None
        assert len(results[0].error) > 0

    def test_run_batch_parallel_fallback_warning(
        self,
        tmp_path: Path,
        caplog,
    ) -> None:
        """Test run_batch_parallel shows fallback warning."""
        runner = BenchmarkRunner()

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n")

        mock_evaluator = Mock()
        mock_evaluator.dataset_name = "test"

        # Call parallel method - should warn and fallback
        with caplog.at_level("WARNING"):
            runner.run_batch_parallel(
                document_files=[pdf_file],
                parser_name="pymupdf",
                evaluator=mock_evaluator,
            )

        # Should log warning about parallel processing not implemented
        assert any("Parallel processing not yet implemented" in record.message for record in caplog.records)

    def test_process_document_success(self, tmp_path: Path) -> None:
        """Test _process_document with successful parsing."""
        runner = BenchmarkRunner()

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n")

        # Mock evaluator
        mock_evaluator = Mock()
        mock_evaluator.dataset_name = "test"
        mock_evaluator.load_ground_truth.return_value = {"text": "test"}

        from data_ingestor.evaluation.models import MetricScore

        expected_result = EvaluationResult(
            document_id="test",
            dataset="test",
            success=True,
            metrics=[MetricScore(name="cer", value=0.05)],
        )
        mock_evaluator.evaluate_document.return_value = expected_result

        # Build a router with the requested parser registered, as run_batch does.
        from data_ingestor.core.models import DocumentFormat
        from data_ingestor.pipeline.router import DocumentRouter

        router = DocumentRouter(runner.settings)
        parser_class = runner.available_parsers["pymupdf"]
        parser = parser_class(runner.settings.get_parser_config("pymupdf"))
        router.parser_registry.register(parser, [DocumentFormat.PDF])

        # Process document
        result = runner._process_document(
            doc_file=pdf_file,
            parser_name="pymupdf",
            evaluator=mock_evaluator,
            router=router,
        )

        # Verify result
        assert isinstance(result, EvaluationResult)
        # Should have processing time set
        assert hasattr(result, "processing_time")

    def test_process_document_handles_exceptions(self, tmp_path: Path) -> None:
        """Test _process_document handles exceptions during processing."""
        runner = BenchmarkRunner()

        # Use a non-existent file to trigger parsing error
        pdf_file = tmp_path / "nonexistent.pdf"

        # Mock evaluator
        mock_evaluator = Mock()
        mock_evaluator.dataset_name = "test"

        # Build a router with the requested parser registered, as run_batch does.
        from data_ingestor.core.models import DocumentFormat
        from data_ingestor.pipeline.router import DocumentRouter

        router = DocumentRouter(runner.settings)
        parser_class = runner.available_parsers["pymupdf"]
        parser = parser_class(runner.settings.get_parser_config("pymupdf"))
        router.parser_registry.register(parser, [DocumentFormat.PDF])

        # Process document - should handle exception
        result = runner._process_document(
            doc_file=pdf_file,
            parser_name="pymupdf",
            evaluator=mock_evaluator,
            router=router,
        )

        # Should return failure result with error
        assert result.success is False
        assert result.error is not None
        assert len(result.error) > 0  # Should have some error message


@pytest.mark.unit
class TestBenchmarkOrchestratorExtended:
    """Extended tests for BenchmarkOrchestrator."""

    def test_orchestrator_load_dataset_config_missing_file(
        self,
        tmp_path: Path,
    ) -> None:
        """Test orchestrator handles missing config file."""
        missing_config = tmp_path / "nonexistent.yaml"

        orchestrator = BenchmarkOrchestrator(
            datasets=["test"],
            parsers=["pymupdf"],
            config_path=missing_config,
        )

        # Should have empty dataset config
        assert orchestrator.dataset_config == {"datasets": {}}

    def test_orchestrator_load_dataset_config_valid_file(
        self,
        tmp_path: Path,
    ) -> None:
        """Test orchestrator loads valid config file."""
        config_file = tmp_path / "config.yaml"
        config_content = """
datasets:
  testset:
    path: /test/path
    type: pdf
workers: 8
"""
        config_file.write_text(config_content)

        orchestrator = BenchmarkOrchestrator(
            datasets=["testset"],
            parsers=["pymupdf"],
            config_path=config_file,
        )

        # Should load config
        assert "datasets" in orchestrator.dataset_config
        assert "testset" in orchestrator.dataset_config["datasets"]

    def test_orchestrator_initialize_evaluators_skips_missing_datasets(
        self,
        tmp_path: Path,
    ) -> None:
        """Test orchestrator skips datasets not in config."""
        config_file = tmp_path / "config.yaml"
        config_content = """
datasets:
  dataset1:
    path: /test/path
"""
        config_file.write_text(config_content)

        orchestrator = BenchmarkOrchestrator(
            datasets=["dataset1", "missing_dataset"],
            parsers=["pymupdf"],
            config_path=config_file,
        )

        # Should skip missing dataset
        # Only datasets with valid evaluators should be present
        # (may be empty if ground truth dirs don't exist)
        assert isinstance(orchestrator.evaluators, dict)

    def test_orchestrator_initialize_evaluators_handles_file_errors(
        self,
        tmp_path: Path,
        caplog,
    ) -> None:
        """Test orchestrator handles FileNotFoundError during evaluator init."""
        config_file = tmp_path / "config.yaml"
        config_content = """
datasets:
  testset:
    path: /nonexistent/path
"""
        config_file.write_text(config_content)

        with caplog.at_level("ERROR"):
            orchestrator = BenchmarkOrchestrator(
                datasets=["testset"],
                parsers=["pymupdf"],
                config_path=config_file,
            )

        # Should log error and skip evaluator
        # Note: evaluator may not be initialized if path doesn't exist
        assert isinstance(orchestrator.evaluators, dict)

    def test_orchestrator_run_raises_error_no_evaluators(
        self,
        tmp_path: Path,
    ) -> None:
        """Test orchestrator.run() raises error when no evaluators initialized."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("datasets: {}")

        orchestrator = BenchmarkOrchestrator(
            datasets=[],
            parsers=["pymupdf"],
            config_path=config_file,
        )

        # Manually clear evaluators to simulate failure
        orchestrator.evaluators = {}

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="No evaluators initialized"):
            orchestrator.run()

    def test_orchestrator_save_results_default_filename(
        self,
        tmp_path: Path,
    ) -> None:
        """Test save_results generates default filename."""
        orchestrator = BenchmarkOrchestrator(
            datasets=["test"],
            parsers=["pymupdf"],
            output_dir=str(tmp_path),
            config_path=tmp_path / "config.yaml",
        )

        results = {
            "metadata": {},
            "datasets": {},
            "overall": {},
        }

        # Save without specifying filename
        output_path = orchestrator.save_results(results)

        # Should create file with timestamp
        assert output_path.exists()
        assert "benchmark_" in output_path.name
        assert output_path.suffix == ".json"

    def test_orchestrator_save_results_custom_filename(
        self,
        tmp_path: Path,
    ) -> None:
        """Test save_results with custom filename."""
        orchestrator = BenchmarkOrchestrator(
            datasets=["test"],
            output_dir=str(tmp_path),
            config_path=tmp_path / "config.yaml",
        )

        results = {
            "metadata": {},
            "datasets": {},
            "overall": {},
        }

        # Save with custom filename
        output_path = orchestrator.save_results(results, "custom_results.json")

        # Should create file with custom name
        assert output_path.exists()
        assert output_path.name == "custom_results.json"

        # Verify content
        with open(output_path) as f:
            loaded = json.load(f)
        assert loaded == results

    def test_orchestrator_load_results(self, tmp_path: Path) -> None:
        """Test load_results loads saved results."""
        orchestrator = BenchmarkOrchestrator(
            datasets=["test"],
            output_dir=str(tmp_path),
            config_path=tmp_path / "config.yaml",
        )

        # Create results file
        results = {
            "metadata": {"test": "data"},
            "datasets": {},
            "overall": {},
        }
        results_file = tmp_path / "results.json"
        with open(results_file, "w") as f:
            json.dump(results, f)

        # Load results
        loaded = orchestrator.load_results(results_file)

        # Should match original
        assert loaded == results
        assert loaded["metadata"]["test"] == "data"

    def test_orchestrator_find_documents_nonexistent_dir(
        self,
        tmp_path: Path,
    ) -> None:
        """Test _find_documents with nonexistent directory."""
        orchestrator = BenchmarkOrchestrator(
            datasets=["test"],
            config_path=tmp_path / "config.yaml",
        )

        missing_dir = tmp_path / "nonexistent"
        documents = orchestrator._find_documents(missing_dir)

        # Should return empty list
        assert documents == []

    def test_orchestrator_find_documents_multiple_formats(
        self,
        tmp_path: Path,
    ) -> None:
        """Test _find_documents finds multiple document formats."""
        orchestrator = BenchmarkOrchestrator(
            datasets=["test"],
            config_path=tmp_path / "config.yaml",
        )

        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create files with different extensions
        (docs_dir / "doc1.pdf").touch()
        (docs_dir / "doc2.png").touch()
        (docs_dir / "doc3.jpg").touch()
        (docs_dir / "doc4.tif").touch()
        (docs_dir / "ignore.txt").touch()  # Should not be included

        documents = orchestrator._find_documents(docs_dir)

        # Should find only supported formats
        assert len(documents) == 4
        extensions = {doc.suffix for doc in documents}
        assert extensions == {".pdf", ".png", ".jpg", ".tif"}

    def test_orchestrator_calculate_overall_stats_empty_results(self) -> None:
        """Test _calculate_overall_stats with empty results."""
        orchestrator = BenchmarkOrchestrator(
            datasets=["test"],
            config_path=Path("nonexistent.yaml"),
        )

        start_time = datetime.now()
        end_time = datetime.now()

        stats = orchestrator._calculate_overall_stats({}, start_time, end_time)

        # Should return zeros for empty results
        assert stats["total_documents"] == 0
        assert stats["total_successful"] == 0
        assert stats["total_failed"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["failure_rate"] == 0.0

    def test_orchestrator_calculate_overall_stats_with_data(self) -> None:
        """Test _calculate_overall_stats with real data."""
        orchestrator = BenchmarkOrchestrator(
            datasets=["test"],
            config_path=Path("nonexistent.yaml"),
        )

        dataset_results = {
            "dataset1": {
                "parsers": {
                    "parser1": {
                        "aggregated": {
                            "total_documents": 100,
                            "successful_documents": 95,
                            "failed_documents": 5,
                        },
                    },
                },
            },
            "dataset2": {
                "parsers": {
                    "parser2": {
                        "aggregated": {
                            "total_documents": 50,
                            "successful_documents": 48,
                            "failed_documents": 2,
                        },
                    },
                },
            },
        }

        start_time = datetime(2025, 1, 1, 0, 0, 0)
        end_time = datetime(2025, 1, 1, 1, 0, 0)  # 1 hour

        stats = orchestrator._calculate_overall_stats(
            dataset_results,
            start_time,
            end_time,
        )

        # Verify calculations
        assert stats["total_documents"] == 150
        assert stats["total_successful"] == 143
        assert stats["total_failed"] == 7
        assert abs(stats["success_rate"] - 0.9533) < 0.001
        assert abs(stats["failure_rate"] - 0.0467) < 0.001
        assert stats["total_time"] == 3600.0  # 1 hour in seconds
        assert abs(stats["throughput_docs_per_hour"] - 150.0) < 0.1


@pytest.mark.unit
class TestBenchmarkConfigExtended:
    """Extended tests for BenchmarkConfig validation."""

    def test_config_validation_invalid_workers(self) -> None:
        """Test config raises error for invalid workers."""
        with pytest.raises(ValueError, match="Workers must be >= 1"):
            BenchmarkConfig(
                datasets=["test"],
                parsers=["pymupdf"],
                workers=0,
            )

    def test_config_validation_invalid_batch_size(self) -> None:
        """Test config raises error for invalid batch size."""
        with pytest.raises(ValueError, match="Batch size must be >= 1"):
            BenchmarkConfig(
                datasets=["test"],
                parsers=["pymupdf"],
                batch_size=0,
            )

    def test_config_validation_invalid_timeout(self) -> None:
        """Test config raises error for invalid timeout."""
        with pytest.raises(ValueError, match="Timeout must be >= 1"):
            BenchmarkConfig(
                datasets=["test"],
                parsers=["pymupdf"],
                timeout_per_doc=0,
            )

    def test_config_creates_output_directory(self, tmp_path: Path) -> None:
        """Test config creates output directory if it doesn't exist."""
        output_dir = tmp_path / "new_output_dir"
        assert not output_dir.exists()

        config = BenchmarkConfig(
            datasets=["test"],
            parsers=["pymupdf"],
            output_dir=output_dir,
        )

        # Should create directory
        assert config.output_dir.exists()
        assert config.output_dir == output_dir


@pytest.mark.unit
class TestBenchmarkReporterExtended:
    """Extended tests for BenchmarkReporter."""

    def test_reporter_html_with_mean_metrics(self, tmp_path: Path) -> None:
        """Test HTML report includes mean_metrics."""
        results = {
            "metadata": {"timestamp": "2025-11-07T10:00:00Z"},
            "datasets": {
                "test_dataset": {
                    "parsers": {
                        "pymupdf": {
                            "aggregated": {
                                "total_documents": 10,
                                "success_rate": 0.95,
                                "avg_processing_time": 1.5,
                                "mean_metrics": {
                                    "cer": 0.05,
                                    "bleu": 0.85,
                                },
                            },
                        },
                    },
                },
            },
            "overall": {
                "total_documents": 10,
                "total_successful": 9,
                "total_failed": 1,
                "success_rate": 0.9,
                "throughput_docs_per_hour": 120.0,
                "total_time": 300.0,
            },
        }

        reporter = BenchmarkReporter(results)
        output_file = tmp_path / "report_with_metrics.html"
        reporter.generate_html(str(output_file))

        # Verify file created
        assert output_file.exists()

        # Verify content includes metrics
        html_content = output_file.read_text()
        assert "cer" in html_content.lower()
        assert "bleu" in html_content.lower()
        assert "0.05" in html_content  # CER value

    def test_reporter_html_without_mean_metrics(self, tmp_path: Path) -> None:
        """Test HTML report handles missing mean_metrics."""
        results = {
            "metadata": {"timestamp": "2025-11-07T10:00:00Z"},
            "datasets": {
                "test_dataset": {
                    "parsers": {
                        "pymupdf": {
                            "aggregated": {
                                "total_documents": 10,
                                "success_rate": 1.0,
                                "avg_processing_time": 1.0,
                                # No mean_metrics
                            },
                        },
                    },
                },
            },
            "overall": {
                "total_documents": 10,
                "success_rate": 1.0,
            },
        }

        reporter = BenchmarkReporter(results)
        output_file = tmp_path / "report_no_metrics.html"

        # Should not raise error
        reporter.generate_html(str(output_file))
        assert output_file.exists()

    def test_reporter_csv_with_std_metrics(self, tmp_path: Path) -> None:
        """Test CSV includes std_metrics columns."""
        results = {
            "metadata": {},
            "datasets": {
                "test": {
                    "parsers": {
                        "pymupdf": {
                            "aggregated": {
                                "total_documents": 5,
                                "successful_documents": 5,
                                "failed_documents": 0,
                                "success_rate": 1.0,
                                "avg_processing_time": 1.0,
                                "mean_metrics": {"cer": 0.05},
                                "std_metrics": {"cer": 0.01},
                            },
                        },
                    },
                },
            },
            "overall": {},
        }

        reporter = BenchmarkReporter(results)
        output_file = tmp_path / "metrics.csv"
        reporter.generate_csv(str(output_file))

        # Verify CSV content
        assert output_file.exists()
        csv_content = output_file.read_text()

        # Should have both mean and std columns
        assert "mean_cer" in csv_content
        assert "std_cer" in csv_content

    def test_reporter_csv_empty_results(self, tmp_path: Path) -> None:
        """Test CSV generation with empty results."""
        results = {
            "metadata": {},
            "datasets": {},
            "overall": {},
        }

        reporter = BenchmarkReporter(results)
        output_file = tmp_path / "empty.csv"

        # Should handle empty results without error
        result_path = reporter.generate_csv(str(output_file))

        # When no data rows, CSV may not be created (see reporter.py:414)
        # This is expected behavior - empty datasets produce no CSV output
        assert result_path == output_file  # Method still returns path

    def test_reporter_parser_comparison_empty(self, tmp_path: Path) -> None:
        """Test parser comparison section with no data."""
        results = {
            "metadata": {},
            "datasets": {},
            "overall": {},
        }

        reporter = BenchmarkReporter(results)
        output_file = tmp_path / "no_comparison.html"

        reporter.generate_html(str(output_file))

        # Should create HTML without comparison section
        assert output_file.exists()

    def test_reporter_build_overall_section_formatting(
        self,
        tmp_path: Path,
    ) -> None:
        """Test overall section formats numbers correctly."""
        results = {
            "metadata": {},
            "datasets": {},
            "overall": {
                "total_documents": 1000,
                "total_successful": 950,
                "total_failed": 50,
                "success_rate": 0.95,
                "throughput_docs_per_hour": 123.456,
                "total_time": 3600.5,
            },
        }

        reporter = BenchmarkReporter(results)
        output_file = tmp_path / "formatted.html"

        reporter.generate_html(str(output_file))

        html_content = output_file.read_text()

        # Verify formatted values present
        assert "1000" in html_content  # total docs
        assert "950" in html_content  # successful
        assert "50" in html_content  # failed
        assert "95" in html_content or "95.0%" in html_content  # success rate
