"""
Data models for evaluation results and metrics.

Defines the structure for evaluation outputs, including individual metrics,
per-document results, and aggregated statistics across datasets.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MetricType(str, Enum):
    """Types of evaluation metrics."""

    # Text fidelity metrics
    CER = "character_error_rate"  # Character Error Rate
    BLEU = "bleu_score"  # BLEU score
    CHRF = "chrf_score"  # Character n-gram F-score

    # Structure metrics
    SECTION_F1 = "section_f1"  # Section detection F1
    LIST_F1 = "list_f1"  # List extraction F1
    READING_ORDER_F1 = "reading_order_f1"  # Reading order F1
    KENDALL_TAU = "kendall_tau"  # Rank correlation

    # Layout metrics
    MAP = "mean_average_precision"  # mAP for layout classes
    LAYOUT_F1 = "layout_f1"  # Layout detection F1

    # Table metrics
    TEDS = "tree_edit_distance"  # Tree Edit Distance Score
    CELL_MATCH = "cell_exact_match"  # Cell exact match
    HEADER_F1 = "header_f1"  # Header F1 score

    # Overall quality
    QUALITY_SCORE = "quality_score"  # Overall quality (0.0-1.0)


@dataclass
class MetricScore:
    """
    Individual metric score with metadata.

    Attributes:
        name: Metric name (from MetricType)
        value: Metric value (interpretation depends on metric type)
        confidence: Optional confidence interval or std dev
        metadata: Additional metric-specific information
    """

    name: str
    value: float
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate metric score."""
        if self.value < 0:
            raise ValueError(f"Metric value cannot be negative: {self.value}")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "name": self.name,
            "value": self.value,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class EvaluationResult:
    """
    Evaluation result for a single document.

    Contains all metrics computed for one document against its ground truth.

    Attributes:
        document_id: Unique document identifier
        dataset: Dataset name (readoc, doclaynet, pubtables)
        metrics: List of metric scores
        success: Whether evaluation succeeded
        error: Error message if evaluation failed
        processing_time: Time taken for evaluation (seconds)
        timestamp: When evaluation was performed
    """

    document_id: str
    dataset: str
    metrics: list[MetricScore] = field(default_factory=list)
    success: bool = True
    error: str | None = None
    processing_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def get_metric(self, metric_name: str) -> MetricScore | None:
        """
        Get specific metric by name.

        Args:
            metric_name: Name of metric to retrieve

        Returns:
            MetricScore if found, None otherwise
        """
        for metric in self.metrics:
            if metric.name == metric_name:
                return metric
        return None

    def get_metric_value(self, metric_name: str) -> float | None:
        """
        Get metric value by name.

        Args:
            metric_name: Name of metric to retrieve

        Returns:
            Metric value if found, None otherwise
        """
        metric = self.get_metric(metric_name)
        return metric.value if metric else None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "document_id": self.document_id,
            "dataset": self.dataset,
            "metrics": [m.to_dict() for m in self.metrics],
            "success": self.success,
            "error": self.error,
            "processing_time": self.processing_time,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AggregatedMetrics:
    """
    Aggregated metrics across multiple documents.

    Computed from a collection of EvaluationResult objects.

    Attributes:
        dataset: Dataset name
        total_documents: Total number of documents evaluated
        successful_documents: Number of successful evaluations
        failed_documents: Number of failed evaluations
        mean_metrics: Mean value for each metric
        std_metrics: Standard deviation for each metric
        min_metrics: Minimum value for each metric
        max_metrics: Maximum value for each metric
        processing_time_total: Total processing time (seconds)
        timestamp: When aggregation was performed
    """

    dataset: str
    total_documents: int
    successful_documents: int
    failed_documents: int
    mean_metrics: dict[str, float] = field(default_factory=dict)
    std_metrics: dict[str, float] = field(default_factory=dict)
    min_metrics: dict[str, float] = field(default_factory=dict)
    max_metrics: dict[str, float] = field(default_factory=dict)
    processing_time_total: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def success_rate(self) -> float:
        """Calculate success rate (0.0-1.0)."""
        if self.total_documents == 0:
            return 0.0
        return self.successful_documents / self.total_documents

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate (0.0-1.0)."""
        return 1.0 - self.success_rate

    @property
    def avg_processing_time(self) -> float:
        """Calculate average processing time per document."""
        if self.total_documents == 0:
            return 0.0
        return self.processing_time_total / self.total_documents

    def get_mean_metric(self, metric_name: str) -> float | None:
        """Get mean value for specific metric."""
        return self.mean_metrics.get(metric_name)

    def get_std_metric(self, metric_name: str) -> float | None:
        """Get standard deviation for specific metric."""
        return self.std_metrics.get(metric_name)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "dataset": self.dataset,
            "total_documents": self.total_documents,
            "successful_documents": self.successful_documents,
            "failed_documents": self.failed_documents,
            "success_rate": self.success_rate,
            "failure_rate": self.failure_rate,
            "mean_metrics": self.mean_metrics,
            "std_metrics": self.std_metrics,
            "min_metrics": self.min_metrics,
            "max_metrics": self.max_metrics,
            "processing_time_total": self.processing_time_total,
            "avg_processing_time": self.avg_processing_time,
            "timestamp": self.timestamp.isoformat(),
        }
