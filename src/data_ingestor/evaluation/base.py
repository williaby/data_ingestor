"""
Base evaluator abstract class.

Defines the interface for all dataset-specific evaluators. Each evaluator
implements document-level evaluation and result aggregation for its dataset.
"""

import time
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np

from data_ingestor.core.models import Document
from data_ingestor.evaluation.models import (
    AggregatedMetrics,
    EvaluationResult,
)


class BaseEvaluator(ABC):
    """
    Abstract base class for dataset evaluators.

    Each dataset (ReadOC, DocLayNet, PubTables) has a specific evaluator
    that inherits from this class and implements dataset-specific metrics.

    Attributes:
        dataset_name: Name of the dataset (e.g., "readoc", "doclaynet")
        ground_truth_dir: Path to ground truth annotations
    """

    def __init__(
        self,
        dataset_name: str,
        ground_truth_dir: Path,
    ) -> None:
        """
        Initialize evaluator.

        Args:
            dataset_name: Name of the dataset
            ground_truth_dir: Path to ground truth annotations
        """
        self.dataset_name = dataset_name
        self.ground_truth_dir = Path(ground_truth_dir)

        # Validate ground truth directory
        if not self.ground_truth_dir.exists():
            raise FileNotFoundError(
                f"Ground truth directory not found: {self.ground_truth_dir}",
            )

    @abstractmethod
    def evaluate_document(
        self,
        predicted: Document,
        ground_truth: dict,
    ) -> EvaluationResult:
        """
        Evaluate a single document against ground truth.

        Args:
            predicted: Parsed document from our pipeline
            ground_truth: Ground truth annotations (format varies by dataset)

        Returns:
            EvaluationResult with all computed metrics

        Raises:
            ValueError: If document or ground truth is invalid
        """

    def evaluate_batch(
        self,
        documents: list[tuple[Document, dict]],
    ) -> list[EvaluationResult]:
        """
        Evaluate multiple documents.

        Args:
            documents: List of (predicted_doc, ground_truth) tuples

        Returns:
            List of EvaluationResult objects
        """
        results = []

        for predicted, ground_truth in documents:
            try:
                start_time = time.time()
                result = self.evaluate_document(predicted, ground_truth)
                result.processing_time = time.time() - start_time
                results.append(result)

            except Exception as e:
                # #CRITICAL: Evaluation errors should not halt batch processing
                # #VERIFY: Error is logged and batch continues
                results.append(
                    EvaluationResult(
                        document_id=predicted.metadata.get(
                            "doc_id",
                            "unknown",
                        ),
                        dataset=self.dataset_name,
                        success=False,
                        error=str(e),
                    ),
                )

        return results

    def aggregate_results(
        self,
        results: list[EvaluationResult],
    ) -> AggregatedMetrics:
        """
        Aggregate individual results into dataset-level metrics.

        Computes mean, std, min, max for each metric across all documents.

        Args:
            results: List of EvaluationResult objects

        Returns:
            AggregatedMetrics with statistics across all documents
        """
        # Filter successful evaluations
        successful_results = [r for r in results if r.success]

        # Calculate basic stats
        aggregated = AggregatedMetrics(
            dataset=self.dataset_name,
            total_documents=len(results),
            successful_documents=len(successful_results),
            failed_documents=len(results) - len(successful_results),
            processing_time_total=sum(r.processing_time for r in results),
        )

        if not successful_results:
            return aggregated

        # Collect all metric names
        metric_names = set()
        for result in successful_results:
            for metric in result.metrics:
                metric_names.add(metric.name)

        # Compute statistics for each metric
        for metric_name in metric_names:
            # Collect values for this metric
            values = []
            for result in successful_results:
                metric = result.get_metric(metric_name)
                if metric:
                    values.append(metric.value)

            if values:
                # #ASSUME: numpy is available for statistical calculations
                # #VERIFY: All metrics have valid numeric values
                aggregated.mean_metrics[metric_name] = float(np.mean(values))
                aggregated.std_metrics[metric_name] = float(np.std(values))
                aggregated.min_metrics[metric_name] = float(np.min(values))
                aggregated.max_metrics[metric_name] = float(np.max(values))

        return aggregated

    def load_ground_truth(
        self,
        document_id: str,
    ) -> dict | None:
        """
        Load ground truth for a specific document.

        Args:
            document_id: Document identifier

        Returns:
            Ground truth dict, or None if not found

        Note:
            Subclasses can override this for dataset-specific loading.
        """
        # Default implementation looks for JSON file
        gt_path = self.ground_truth_dir / f"{document_id}.json"

        if not gt_path.exists():
            return None

        import json

        with open(gt_path) as f:
            return json.load(f)

    def validate_document(
        self,
        predicted: Document,
        ground_truth: dict,
    ) -> None:
        """
        Validate document and ground truth are compatible.

        Args:
            predicted: Parsed document
            ground_truth: Ground truth annotations

        Raises:
            ValueError: If validation fails
        """
        if not predicted:
            raise ValueError("Predicted document is None or empty")

        if not ground_truth:
            raise ValueError("Ground truth is None or empty")

        # #ASSUME: Document has metadata dict
        # #VERIFY: Basic structure validation passes
        if not hasattr(predicted, "metadata"):
            raise ValueError("Document missing metadata attribute")

    def get_baseline_targets(self) -> dict[str, float]:
        """
        Get baseline target metrics for this dataset.

        Returns:
            Dict mapping metric names to target values

        Note:
            Subclasses should override with dataset-specific targets.
        """
        return {}

    def compare_to_baseline(
        self,
        aggregated: AggregatedMetrics,
    ) -> dict[str, dict[str, float]]:
        """
        Compare aggregated metrics to baseline targets.

        Args:
            aggregated: Aggregated metrics to compare

        Returns:
            Dict with comparison results:
            {
                "metric_name": {
                    "value": actual_value,
                    "target": target_value,
                    "delta": difference,
                    "meets_target": boolean
                }
            }
        """
        targets = self.get_baseline_targets()
        comparison = {}

        for metric_name, target_value in targets.items():
            actual_value = aggregated.get_mean_metric(metric_name)

            if actual_value is not None:
                # #ASSUME: Lower is better for error metrics (CER)
                # #ASSUME: Higher is better for F1/accuracy metrics
                # #VERIFY: Metric direction is correct for comparison
                is_error_metric = "error" in metric_name.lower()

                if is_error_metric:
                    meets_target = actual_value <= target_value
                    delta = target_value - actual_value
                else:
                    meets_target = actual_value >= target_value
                    delta = actual_value - target_value

                comparison[metric_name] = {
                    "value": actual_value,
                    "target": target_value,
                    "delta": delta,
                    "meets_target": meets_target,
                }

        return comparison
