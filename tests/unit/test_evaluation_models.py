"""
Unit tests for evaluation data models.

Tests MetricScore, EvaluationResult, and AggregatedMetrics.
"""

import pytest

from data_ingestor.evaluation.models import (
    AggregatedMetrics,
    EvaluationResult,
    MetricScore,
)


class TestMetricScore:
    """Test MetricScore dataclass."""

    def test_creation(self):
        """Test basic metric creation."""
        metric = MetricScore(name="cer", value=0.05)
        assert metric.name == "cer"
        assert metric.value == 0.05
        assert metric.confidence is None

    def test_with_confidence(self):
        """Test metric with confidence value."""
        metric = MetricScore(name="f1", value=0.95, confidence=0.02)
        assert metric.confidence == 0.02

    def test_with_metadata(self):
        """Test metric with metadata."""
        metadata = {"source": "test", "version": "1.0"}
        metric = MetricScore(name="bleu", value=0.8, metadata=metadata)
        assert metric.metadata == metadata

    def test_negative_value_raises_error(self):
        """Test that negative values raise ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            MetricScore(name="cer", value=-0.1)

    def test_to_dict(self):
        """Test conversion to dictionary."""
        metric = MetricScore(
            name="chrf",
            value=0.85,
            confidence=0.03,
            metadata={"beta": 2.0},
        )
        d = metric.to_dict()
        assert d["name"] == "chrf"
        assert d["value"] == 0.85
        assert d["confidence"] == 0.03
        assert d["metadata"]["beta"] == 2.0


class TestEvaluationResult:
    """Test EvaluationResult dataclass."""

    def test_creation(self):
        """Test basic result creation."""
        result = EvaluationResult(
            document_id="doc123",
            dataset="test_dataset",
        )
        assert result.document_id == "doc123"
        assert result.dataset == "test_dataset"
        assert result.success is True
        assert len(result.metrics) == 0

    def test_with_metrics(self):
        """Test result with metrics."""
        metrics = [
            MetricScore(name="cer", value=0.05),
            MetricScore(name="f1", value=0.95),
        ]
        result = EvaluationResult(
            document_id="doc123",
            dataset="readoc",
            metrics=metrics,
        )
        assert len(result.metrics) == 2

    def test_failed_result(self):
        """Test failed evaluation result."""
        result = EvaluationResult(
            document_id="doc123",
            dataset="readoc",
            success=False,
            error="Parse error",
        )
        assert result.success is False
        assert result.error == "Parse error"

    def test_get_metric(self):
        """Test getting specific metric by name."""
        metrics = [
            MetricScore(name="cer", value=0.05),
            MetricScore(name="f1", value=0.95),
        ]
        result = EvaluationResult(
            document_id="doc123",
            dataset="readoc",
            metrics=metrics,
        )

        cer = result.get_metric("cer")
        assert cer is not None
        assert cer.value == 0.05

        missing = result.get_metric("bleu")
        assert missing is None

    def test_get_metric_value(self):
        """Test getting metric value by name."""
        metrics = [MetricScore(name="f1", value=0.95)]
        result = EvaluationResult(
            document_id="doc123",
            dataset="readoc",
            metrics=metrics,
        )

        assert result.get_metric_value("f1") == 0.95
        assert result.get_metric_value("missing") is None

    def test_to_dict(self):
        """Test conversion to dictionary."""
        metrics = [MetricScore(name="cer", value=0.05)]
        result = EvaluationResult(
            document_id="doc123",
            dataset="readoc",
            metrics=metrics,
            processing_time=1.5,
        )

        d = result.to_dict()
        assert d["document_id"] == "doc123"
        assert d["dataset"] == "readoc"
        assert d["success"] is True
        assert d["processing_time"] == 1.5
        assert len(d["metrics"]) == 1
        assert "timestamp" in d


class TestAggregatedMetrics:
    """Test AggregatedMetrics dataclass."""

    def test_creation(self):
        """Test basic aggregated metrics creation."""
        agg = AggregatedMetrics(
            dataset="readoc",
            total_documents=100,
            successful_documents=95,
            failed_documents=5,
        )
        assert agg.dataset == "readoc"
        assert agg.total_documents == 100
        assert agg.successful_documents == 95
        assert agg.failed_documents == 5

    def test_success_rate(self):
        """Test success rate calculation."""
        agg = AggregatedMetrics(
            dataset="test",
            total_documents=100,
            successful_documents=95,
            failed_documents=5,
        )
        assert agg.success_rate == 0.95

    def test_success_rate_zero_documents(self):
        """Test success rate with zero documents."""
        agg = AggregatedMetrics(
            dataset="test",
            total_documents=0,
            successful_documents=0,
            failed_documents=0,
        )
        assert agg.success_rate == 0.0

    def test_failure_rate(self):
        """Test failure rate calculation."""
        agg = AggregatedMetrics(
            dataset="test",
            total_documents=100,
            successful_documents=95,
            failed_documents=5,
        )
        assert abs(agg.failure_rate - 0.05) < 0.001

    def test_avg_processing_time(self):
        """Test average processing time calculation."""
        agg = AggregatedMetrics(
            dataset="test",
            total_documents=10,
            successful_documents=10,
            failed_documents=0,
            processing_time_total=50.0,
        )
        assert agg.avg_processing_time == 5.0

    def test_avg_processing_time_zero_documents(self):
        """Test average processing time with zero documents."""
        agg = AggregatedMetrics(
            dataset="test",
            total_documents=0,
            successful_documents=0,
            failed_documents=0,
        )
        assert agg.avg_processing_time == 0.0

    def test_get_mean_metric(self):
        """Test getting mean metric value."""
        agg = AggregatedMetrics(
            dataset="test",
            total_documents=10,
            successful_documents=10,
            failed_documents=0,
            mean_metrics={"cer": 0.05, "f1": 0.95},
        )
        assert agg.get_mean_metric("cer") == 0.05
        assert agg.get_mean_metric("f1") == 0.95
        assert agg.get_mean_metric("missing") is None

    def test_get_std_metric(self):
        """Test getting standard deviation metric value."""
        agg = AggregatedMetrics(
            dataset="test",
            total_documents=10,
            successful_documents=10,
            failed_documents=0,
            std_metrics={"cer": 0.01, "f1": 0.02},
        )
        assert agg.get_std_metric("cer") == 0.01
        assert agg.get_std_metric("missing") is None

    def test_to_dict(self):
        """Test conversion to dictionary."""
        agg = AggregatedMetrics(
            dataset="readoc",
            total_documents=100,
            successful_documents=95,
            failed_documents=5,
            mean_metrics={"cer": 0.05},
            processing_time_total=150.0,
        )

        d = agg.to_dict()
        assert d["dataset"] == "readoc"
        assert d["total_documents"] == 100
        assert d["successful_documents"] == 95
        assert d["failed_documents"] == 5
        assert d["success_rate"] == 0.95
        assert abs(d["failure_rate"] - 0.05) < 0.001
        assert d["mean_metrics"]["cer"] == 0.05
        assert d["processing_time_total"] == 150.0
        assert "timestamp" in d
