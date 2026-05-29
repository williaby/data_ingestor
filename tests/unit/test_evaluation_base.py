"""
Unit tests for BaseEvaluator abstract class.

Tests base functionality with a concrete test implementation.
"""

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from data_ingestor.core.models import (
    Document,
    DocumentFormat,
    ProcessingStatus,
)
from data_ingestor.evaluation.base import BaseEvaluator
from data_ingestor.evaluation.models import (
    AggregatedMetrics,
    EvaluationResult,
    MetricScore,
)


class TestEvaluator(BaseEvaluator):
    """Concrete evaluator for testing BaseEvaluator."""

    def evaluate_document(self, predicted, ground_truth):
        """Simple test implementation."""
        # Validate inputs
        self.validate_document(predicted, ground_truth)

        # Create mock metrics
        metrics = [
            MetricScore(name="cer", value=0.05),
            MetricScore(name="f1", value=0.95),
        ]

        return EvaluationResult(
            document_id=predicted.document_id,
            dataset=self.dataset_name,
            metrics=metrics,
            success=True,
        )

    def get_baseline_targets(self):
        """Return test baseline targets."""
        return {
            "cer": 0.10,  # Lower is better
            "f1": 0.90,  # Higher is better
        }


class TestBaseEvaluator:
    """Test BaseEvaluator abstract class."""

    @pytest.fixture
    def temp_gt_dir(self):
        """Create temporary ground truth directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gt_dir = Path(tmpdir)
            yield gt_dir

    @pytest.fixture
    def evaluator(self, temp_gt_dir):
        """Create test evaluator instance."""
        return TestEvaluator("test_dataset", temp_gt_dir)

    @pytest.fixture
    def sample_document(self):
        """Create sample document for testing."""
        return Document(
            document_id="test_doc_1",
            source_path=None,
            format=DocumentFormat.PDF,
            status=ProcessingStatus.COMPLETED,
            created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            metadata={"page_count": 1, "title": "Test Document"},
        )

    @pytest.fixture
    def sample_ground_truth(self):
        """Create sample ground truth data."""
        return {
            "doc_id": "test_doc_1",
            "text": "Test content",
            "elements": [{"type": "text", "content": "Test content"}],
        }

    def test_initialization(self, temp_gt_dir):
        """Test evaluator initialization."""
        evaluator = TestEvaluator("test_dataset", temp_gt_dir)
        assert evaluator.dataset_name == "test_dataset"
        assert evaluator.ground_truth_dir == temp_gt_dir

    def test_initialization_missing_directory(self):
        """Test initialization with missing ground truth directory."""
        with pytest.raises(FileNotFoundError, match="Ground truth directory not found"):
            TestEvaluator("test_dataset", Path("/nonexistent/path"))

    def test_evaluate_document(self, evaluator, sample_document, sample_ground_truth):
        """Test single document evaluation."""
        result = evaluator.evaluate_document(sample_document, sample_ground_truth)

        assert result.success is True
        assert result.document_id == "test_doc_1"
        assert result.dataset == "test_dataset"
        assert len(result.metrics) == 2

        cer = result.get_metric("cer")
        assert cer is not None
        assert cer.value == 0.05

    def test_evaluate_batch_success(self, evaluator, sample_document, sample_ground_truth):
        """Test batch evaluation with all successful."""
        documents = [
            (sample_document, sample_ground_truth),
            (sample_document, sample_ground_truth),
        ]

        results = evaluator.evaluate_batch(documents)

        assert len(results) == 2
        assert all(r.success for r in results)
        assert all(r.processing_time > 0 for r in results)

    def test_evaluate_batch_with_failures(self, evaluator, sample_document):
        """Test batch evaluation with some failures."""
        # Create invalid ground truth that will fail validation
        invalid_gt = None

        documents = [
            (sample_document, {"valid": "data"}),
            (sample_document, invalid_gt),  # Will fail
        ]

        results = evaluator.evaluate_batch(documents)

        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False
        assert results[1].error is not None

    def test_aggregate_results_success(self, evaluator):
        """Test aggregating successful results."""
        results = [
            EvaluationResult(
                document_id="doc1",
                dataset="test",
                metrics=[
                    MetricScore(name="cer", value=0.05),
                    MetricScore(name="f1", value=0.95),
                ],
                processing_time=1.0,
            ),
            EvaluationResult(
                document_id="doc2",
                dataset="test",
                metrics=[
                    MetricScore(name="cer", value=0.10),
                    MetricScore(name="f1", value=0.90),
                ],
                processing_time=2.0,
            ),
        ]

        aggregated = evaluator.aggregate_results(results)

        assert aggregated.dataset == "test_dataset"
        assert aggregated.total_documents == 2
        assert aggregated.successful_documents == 2
        assert aggregated.failed_documents == 0
        assert aggregated.processing_time_total == 3.0

        # Check mean metrics (use abs for floating point comparison)
        assert abs(aggregated.mean_metrics["cer"] - 0.075) < 0.001
        assert abs(aggregated.mean_metrics["f1"] - 0.925) < 0.001

        # Check std metrics
        assert "cer" in aggregated.std_metrics
        assert "f1" in aggregated.std_metrics

        # Check min/max metrics
        assert aggregated.min_metrics["cer"] == 0.05
        assert aggregated.max_metrics["cer"] == 0.10

    def test_aggregate_results_mixed(self, evaluator):
        """Test aggregating with mixed success/failure."""
        results = [
            EvaluationResult(
                document_id="doc1",
                dataset="test",
                metrics=[MetricScore(name="cer", value=0.05)],
                success=True,
            ),
            EvaluationResult(
                document_id="doc2",
                dataset="test",
                success=False,
                error="Failed",
            ),
        ]

        aggregated = evaluator.aggregate_results(results)

        assert aggregated.total_documents == 2
        assert aggregated.successful_documents == 1
        assert aggregated.failed_documents == 1
        assert aggregated.mean_metrics["cer"] == 0.05

    def test_aggregate_results_all_failed(self, evaluator):
        """Test aggregating with all failures."""
        results = [
            EvaluationResult(
                document_id="doc1",
                dataset="test",
                success=False,
                error="Failed",
            ),
        ]

        aggregated = evaluator.aggregate_results(results)

        assert aggregated.total_documents == 1
        assert aggregated.successful_documents == 0
        assert aggregated.failed_documents == 1
        assert len(aggregated.mean_metrics) == 0

    def test_aggregate_results_empty(self, evaluator):
        """Test aggregating empty results."""
        aggregated = evaluator.aggregate_results([])

        assert aggregated.total_documents == 0
        assert aggregated.successful_documents == 0

    def test_load_ground_truth_exists(self, evaluator, temp_gt_dir):
        """Test loading existing ground truth."""
        # Create a ground truth file
        gt_data = {"doc_id": "test123", "text": "Sample text"}
        gt_file = temp_gt_dir / "test123.json"
        with open(gt_file, "w") as f:
            json.dump(gt_data, f)

        loaded = evaluator.load_ground_truth("test123")

        assert loaded is not None
        assert loaded["doc_id"] == "test123"
        assert loaded["text"] == "Sample text"

    def test_load_ground_truth_missing(self, evaluator):
        """Test loading missing ground truth."""
        loaded = evaluator.load_ground_truth("nonexistent")
        assert loaded is None

    def test_validate_document_valid(self, evaluator, sample_document, sample_ground_truth):
        """Test validating valid document and ground truth."""
        # Should not raise
        evaluator.validate_document(sample_document, sample_ground_truth)

    def test_validate_document_none_predicted(self, evaluator, sample_ground_truth):
        """Test validation with None predicted document."""
        with pytest.raises(ValueError, match="Predicted document is None or empty"):
            evaluator.validate_document(None, sample_ground_truth)

    def test_validate_document_none_ground_truth(self, evaluator, sample_document):
        """Test validation with None ground truth."""
        with pytest.raises(ValueError, match="Ground truth is None or empty"):
            evaluator.validate_document(sample_document, None)

    def test_validate_document_empty_ground_truth(self, evaluator, sample_document):
        """Test validation with empty ground truth."""
        with pytest.raises(ValueError, match="Ground truth is None or empty"):
            evaluator.validate_document(sample_document, {})

    def test_validate_document_no_metadata(self, evaluator, sample_ground_truth):
        """Test validation with document missing metadata."""

        # Create document-like object without metadata
        class FakeDoc:
            pass

        fake_doc = FakeDoc()

        with pytest.raises(ValueError, match="missing metadata attribute"):
            evaluator.validate_document(fake_doc, sample_ground_truth)

    def test_get_baseline_targets(self, evaluator):
        """Test getting baseline targets."""
        targets = evaluator.get_baseline_targets()

        assert "cer" in targets
        assert "f1" in targets
        assert targets["cer"] == 0.10
        assert targets["f1"] == 0.90

    def test_compare_to_baseline_meets_targets(self, evaluator):
        """Test baseline comparison when meeting targets."""
        aggregated = AggregatedMetrics(
            dataset="test",
            total_documents=10,
            successful_documents=10,
            failed_documents=0,
            mean_metrics={
                "character_error_rate": 0.05,  # Better than target (0.10), "error" in name
                "f1": 0.95,  # Better than target (0.90)
            },
        )

        # Update baseline targets to match
        evaluator.get_baseline_targets = lambda: {
            "character_error_rate": 0.10,
            "f1": 0.90,
        }

        comparison = evaluator.compare_to_baseline(aggregated)

        assert "character_error_rate" in comparison
        assert "f1" in comparison

        # character_error_rate: "error" in name, lower is better, 0.05 < 0.10
        assert comparison["character_error_rate"]["value"] == 0.05
        assert comparison["character_error_rate"]["target"] == 0.10
        assert comparison["character_error_rate"]["delta"] == 0.05  # target - actual
        assert comparison["character_error_rate"]["meets_target"] is True

        # F1: higher is better, 0.95 > 0.90
        assert comparison["f1"]["value"] == 0.95
        assert comparison["f1"]["target"] == 0.90
        assert abs(comparison["f1"]["delta"] - 0.05) < 0.001  # actual - target
        assert comparison["f1"]["meets_target"] is True

    def test_compare_to_baseline_fails_targets(self, evaluator):
        """Test baseline comparison when failing targets."""
        aggregated = AggregatedMetrics(
            dataset="test",
            total_documents=10,
            successful_documents=10,
            failed_documents=0,
            mean_metrics={
                "character_error_rate": 0.15,  # Worse than target (0.10), "error" in name
                "f1": 0.85,  # Worse than target (0.90)
            },
        )

        # Update baseline targets to match
        evaluator.get_baseline_targets = lambda: {
            "character_error_rate": 0.10,
            "f1": 0.90,
        }

        comparison = evaluator.compare_to_baseline(aggregated)

        # character_error_rate: "error" in name, lower is better, 0.15 > 0.10
        assert comparison["character_error_rate"]["meets_target"] is False
        assert abs(comparison["character_error_rate"]["delta"] - (-0.05)) < 0.001  # target - actual (negative = worse)

        # F1: higher is better, 0.85 < 0.90
        assert comparison["f1"]["meets_target"] is False
        assert abs(comparison["f1"]["delta"] - (-0.05)) < 0.001  # actual - target (negative = worse)

    def test_compare_to_baseline_missing_metrics(self, evaluator):
        """Test baseline comparison with missing metrics."""
        aggregated = AggregatedMetrics(
            dataset="test",
            total_documents=10,
            successful_documents=10,
            failed_documents=0,
            mean_metrics={
                "cer": 0.05,
                # f1 missing
            },
        )

        comparison = evaluator.compare_to_baseline(aggregated)

        # Should only include cer
        assert "cer" in comparison
        assert "f1" not in comparison

    def test_aggregate_results_multiple_metrics(self, evaluator):
        """Test aggregation with multiple different metrics per document."""
        results = [
            EvaluationResult(
                document_id="doc1",
                dataset="test",
                metrics=[
                    MetricScore(name="cer", value=0.05),
                    MetricScore(name="bleu", value=0.85),
                ],
            ),
            EvaluationResult(
                document_id="doc2",
                dataset="test",
                metrics=[
                    MetricScore(name="cer", value=0.10),
                    MetricScore(name="f1", value=0.90),
                ],
            ),
        ]

        aggregated = evaluator.aggregate_results(results)

        # cer appears in both (use abs for floating point comparison)
        assert abs(aggregated.mean_metrics["cer"] - 0.075) < 0.001

        # bleu only in first
        assert aggregated.mean_metrics["bleu"] == 0.85

        # f1 only in second
        assert aggregated.mean_metrics["f1"] == 0.90
