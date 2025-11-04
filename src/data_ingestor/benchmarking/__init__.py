"""
Benchmarking module for Phase 1.5 performance testing.

This module provides orchestration for running comprehensive benchmarks
across multiple datasets and parsers, with parallel processing and
detailed reporting.

Usage:
    from data_ingestor.benchmarking import BenchmarkOrchestrator

    orchestrator = BenchmarkOrchestrator(
        datasets=["readoc", "doclaynet", "pubtables"],
        parsers=["pymupdf", "pymupdf4llm"],
        workers=4,
    )

    results = orchestrator.run()
"""

from data_ingestor.benchmarking.orchestrator import BenchmarkOrchestrator
from data_ingestor.benchmarking.runner import BenchmarkRunner
from data_ingestor.benchmarking.reporter import BenchmarkReporter

__all__ = [
    "BenchmarkOrchestrator",
    "BenchmarkRunner",
    "BenchmarkReporter",
]
