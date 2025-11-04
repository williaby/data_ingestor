"""
Evaluation module for benchmark dataset assessment.

This module provides evaluators for measuring document parsing quality
across multiple industry-standard datasets:

- ReadOC: PDF→Markdown structure fidelity
- DocLayNet: Layout detection and reading order
- PubTables-1M: Table structure recognition

Usage:
    from data_ingestor.evaluation import ReadOCEvaluator, DocLayNetEvaluator

    evaluator = ReadOCEvaluator()
    result = evaluator.evaluate_document(predicted, ground_truth)
"""

from data_ingestor.evaluation.base import BaseEvaluator
from data_ingestor.evaluation.models import (
    AggregatedMetrics,
    EvaluationResult,
    MetricScore,
)
from data_ingestor.evaluation.readoc_evaluator import ReadOCEvaluator
from data_ingestor.evaluation.doclaynet_evaluator import DocLayNetEvaluator
from data_ingestor.evaluation.pubtables_evaluator import PubTablesEvaluator

__all__ = [
    "BaseEvaluator",
    "EvaluationResult",
    "MetricScore",
    "AggregatedMetrics",
    "ReadOCEvaluator",
    "DocLayNetEvaluator",
    "PubTablesEvaluator",
]
