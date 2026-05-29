"""
Benchmarking module for Phase 1b performance testing.

This module provides orchestration for running comprehensive benchmarks
across the DocLayNet dataset with multiple parsers, parallel processing,
and detailed reporting.

Phase 1b focuses on DocLayNet only (81,471 documents) for baseline establishment.

Usage:
    from data_ingestor.benchmarking import BenchmarkOrchestrator

    orchestrator = BenchmarkOrchestrator(
        datasets=["doclaynet"],
        parsers=["pymupdf", "pymupdf4llm"],
        workers=4,
    )

    results = orchestrator.run()
"""

from data_ingestor.benchmarking.orchestrator import BenchmarkOrchestrator
from data_ingestor.benchmarking.reporter import BenchmarkReporter
from data_ingestor.benchmarking.runner import BenchmarkRunner

__all__ = [
    "BenchmarkOrchestrator",
    "BenchmarkReporter",
    "BenchmarkRunner",
]
