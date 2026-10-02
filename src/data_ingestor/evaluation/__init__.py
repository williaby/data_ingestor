"""
Evaluation module for benchmark dataset assessment.

This module provides evaluators for measuring document parsing quality
across industry-standard datasets.

Current Phase 1 dataset:
- DocLayNet: Layout detection and reading order (81,471 documents)

Usage:
    from data_ingestor.evaluation import DocLayNetEvaluator

    evaluator = DocLayNetEvaluator(ground_truth_dir)
    result = evaluator.evaluate_document(predicted, ground_truth)
"""

from data_ingestor.evaluation.base import BaseEvaluator
from data_ingestor.evaluation.doclaynet_evaluator import DocLayNetEvaluator
from data_ingestor.evaluation.models import (
    AggregatedMetrics,
    EvaluationResult,
    MetricScore,
)

__all__ = [
    "AggregatedMetrics",
    "BaseEvaluator",
    "DocLayNetEvaluator",
    "EvaluationResult",
    "MetricScore",
]
