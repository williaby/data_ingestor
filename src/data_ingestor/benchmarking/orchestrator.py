"""
Benchmark orchestrator for coordinating evaluation across datasets.

The orchestrator manages the complete benchmarking workflow:
1. Load dataset configurations
2. Initialize evaluators and parsers
3. Coordinate parallel document processing
4. Aggregate results across datasets
5. Generate reports
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml

from data_ingestor.benchmarking.runner import BenchmarkRunner
from data_ingestor.evaluation import (
    DocLayNetEvaluator,
)
from data_ingestor.evaluation.base import BaseEvaluator

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkConfig:
    """
    Configuration for benchmark run.

    Attributes:
        datasets: List of datasets to evaluate (doclaynet - Phase 1 only)
        parsers: List of parser names to test
        workers: Number of parallel workers
        batch_size: Documents per batch
        output_dir: Directory for results
        timeout_per_doc: Maximum seconds per document
    """

    datasets: list[str]
    parsers: list[str]
    workers: int = 4
    batch_size: int = 32
    output_dir: Path = Path("results")
    timeout_per_doc: int = 120
    save_predictions: bool = True
    config_path: Path | None = None

    def __post_init__(self):
        """Validate configuration."""
        # #CRITICAL: Invalid configuration can cause benchmark failures
        # #VERIFY: All settings are within acceptable ranges
        if self.workers < 1:
            raise ValueError(f"Workers must be >= 1, got {self.workers}")
        if self.batch_size < 1:
            raise ValueError(f"Batch size must be >= 1, got {self.batch_size}")
        if self.timeout_per_doc < 1:
            raise ValueError(
                f"Timeout must be >= 1, got {self.timeout_per_doc}",
            )

        # Ensure output directory exists
        self.output_dir = Path(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)


class BenchmarkOrchestrator:
    """
    Orchestrates benchmark execution across multiple datasets and parsers.

    Coordinates the complete benchmarking workflow including dataset loading,
    parser initialization, parallel processing, result aggregation, and reporting.

    Example:
        >>> orchestrator = BenchmarkOrchestrator(
        ...     datasets=["readoc", "doclaynet"],
        ...     parsers=["pymupdf", "pymupdf4llm"],
        ...     workers=4,
        ... )
        >>> results = orchestrator.run()
        >>> orchestrator.save_results(results, "baseline.json")
    """

    def __init__(
        self,
        datasets: list[str] | None = None,
        parsers: list[str] | None = None,
        workers: int = 4,
        batch_size: int = 32,
        output_dir: str = "results",
        config_path: Path | None = None,
    ):
        """
        Initialize benchmark orchestrator.

        Args:
            datasets: List of datasets to evaluate (default: all)
            parsers: List of parsers to test (default: all available)
            workers: Number of parallel workers (default: 4)
            batch_size: Documents per batch (default: 32)
            output_dir: Output directory for results
            config_path: Path to config YAML (default: data/benchmarks/config.yaml)
        """
        # Load configuration
        if config_path is None:
            config_path = Path("data/benchmarks/config.yaml")

        self.dataset_config = self._load_dataset_config(config_path)

        # Setup benchmark configuration
        if datasets is None:
            datasets = list(self.dataset_config.get("datasets", {}).keys())
        if parsers is None:
            parsers = ["pymupdf", "pymupdf4llm"]  # Default Phase 1 parsers

        self.config = BenchmarkConfig(
            datasets=datasets,
            parsers=parsers,
            workers=workers,
            batch_size=batch_size,
            output_dir=Path(output_dir),
            config_path=config_path,
        )

        # Initialize evaluators
        self.evaluators = self._initialize_evaluators()

        # Initialize runner
        self.runner = BenchmarkRunner(
            workers=self.config.workers,
            batch_size=self.config.batch_size,
            timeout=self.config.timeout_per_doc,
        )

        logger.info("Benchmark orchestrator initialized")
        logger.info(f"Datasets: {self.config.datasets}")
        logger.info(f"Parsers: {self.config.parsers}")
        logger.info(f"Workers: {self.config.workers}")

    def _load_dataset_config(self, config_path: Path) -> dict:
        """
        Load dataset configuration from YAML.

        Args:
            config_path: Path to config file

        Returns:
            Configuration dictionary
        """
        if not config_path.exists():
            logger.warning(
                f"Config file not found: {config_path}. Using defaults.",
            )
            return {"datasets": {}}

        with open(config_path) as f:
            config = yaml.safe_load(f)

        logger.info(f"Loaded configuration from {config_path}")
        return config

    def _initialize_evaluators(self) -> dict[str, BaseEvaluator]:
        """
        Initialize evaluators for each dataset.

        Returns:
            Dict mapping dataset name to evaluator instance
        """
        evaluators = {}

        dataset_configs = self.dataset_config.get("datasets", {})

        for dataset_name in self.config.datasets:
            if dataset_name not in dataset_configs:
                logger.warning(
                    f"Dataset {dataset_name} not in config, skipping",
                )
                continue

            dataset_info = dataset_configs[dataset_name]
            gt_dir = Path(dataset_info["path"]) / "ground_truth"

            # #ASSUME: Ground truth directory exists for each dataset
            # #VERIFY: Directory validation happens in evaluator __init__
            try:
                if dataset_name == "doclaynet":
                    evaluators[dataset_name] = DocLayNetEvaluator(gt_dir)
                else:
                    logger.warning(
                        f"Unknown dataset type: {dataset_name}. Only 'doclaynet' is supported in Phase 1.",
                    )
                    continue

                logger.info(f"Initialized evaluator for {dataset_name}")

            except FileNotFoundError as e:
                logger.error(
                    f"Cannot initialize {dataset_name} evaluator: {e}",
                )

        return evaluators

    def run(self) -> dict[str, any]:
        """
        Run complete benchmark workflow.

        Executes benchmarks across all configured datasets and parsers,
        aggregates results, and returns comprehensive metrics.

        Returns:
            Dict with results:
            {
                "metadata": {...},
                "datasets": {
                    "readoc": {
                        "parsers": {
                            "pymupdf": AggregatedMetrics,
                            ...
                        }
                    },
                    ...
                },
                "overall": {...}
            }

        Raises:
            RuntimeError: If no evaluators are initialized
        """
        if not self.evaluators:
            raise RuntimeError(
                "No evaluators initialized. Check dataset configuration.",
            )

        logger.info("=" * 80)
        logger.info("Starting benchmark run")
        logger.info("=" * 80)

        start_time = datetime.now()

        results = {
            "metadata": {
                "timestamp": start_time.isoformat(),
                "datasets": self.config.datasets,
                "parsers": self.config.parsers,
                "workers": self.config.workers,
                "batch_size": self.config.batch_size,
            },
            "datasets": {},
            "overall": {},
        }

        # Run benchmarks for each dataset
        for dataset_name, evaluator in self.evaluators.items():
            logger.info(f"\nProcessing dataset: {dataset_name}")
            logger.info("-" * 80)

            dataset_results = self._run_dataset_benchmark(
                dataset_name,
                evaluator,
            )
            results["datasets"][dataset_name] = dataset_results

        # Calculate overall statistics
        end_time = datetime.now()
        results["overall"] = self._calculate_overall_stats(
            results["datasets"],
            start_time,
            end_time,
        )

        logger.info("=" * 80)
        logger.info("Benchmark run complete")
        logger.info(f"Total time: {end_time - start_time}")
        logger.info("=" * 80)

        return results

    def _run_dataset_benchmark(
        self,
        dataset_name: str,
        evaluator: BaseEvaluator,
    ) -> dict[str, any]:
        """
        Run benchmark for a single dataset across all parsers.

        Args:
            dataset_name: Dataset identifier
            evaluator: Evaluator instance for this dataset

        Returns:
            Dict with parser results and aggregated metrics
        """
        dataset_results = {"parsers": {}, "aggregated": {}}

        # Get dataset path and configuration
        dataset_info = self.dataset_config["datasets"][dataset_name]

        # Get documents directory (prefer PDF subdirectory if specified)
        if "documents" in dataset_info and "pdf" in dataset_info["documents"]:
            docs_subdir = dataset_info["documents"]["pdf"]
            docs_dir = Path(dataset_info["path"]) / docs_subdir
        else:
            docs_dir = Path(dataset_info["path"]) / "documents"

        # Get sample size from config (default to all documents if not specified)
        sample_size = dataset_info.get("sample_size", None)
        sample_strategy = dataset_info.get("sample_strategy", "random")
        sample_seed = dataset_info.get("sample_seed", 42)

        # Find all documents
        # #ASSUME: Documents directory contains processable files
        # #VERIFY: File extensions match expected formats
        document_files = self._find_documents(
            docs_dir,
            sample_size=sample_size,
            strategy=sample_strategy,
            seed=sample_seed,
        )

        if not document_files:
            logger.warning(f"No documents found in {docs_dir}")
            return dataset_results

        logger.info(f"Found {len(document_files)} documents")

        # Run each parser
        for parser_name in self.config.parsers:
            logger.info(f"\n  Testing parser: {parser_name}")

            parser_results = self.runner.run_batch(
                document_files=document_files,
                parser_name=parser_name,
                evaluator=evaluator,
            )

            # Aggregate results
            aggregated = evaluator.aggregate_results(parser_results)

            dataset_results["parsers"][parser_name] = {
                "results": [r.to_dict() for r in parser_results],
                "aggregated": aggregated.to_dict(),
            }

            # Log summary
            logger.info(f"    Processed: {aggregated.total_documents} docs")
            logger.info(f"    Success rate: {aggregated.success_rate:.2%}")
            logger.info(
                f"    Avg time: {aggregated.avg_processing_time:.2f}s/doc",
            )

        return dataset_results

    def _find_documents(
        self,
        docs_dir: Path,
        sample_size: int | None = None,
        strategy: str = "random",
        seed: int = 42,
    ) -> list[Path]:
        """
        Find all document files in directory with optional sampling.

        Args:
            docs_dir: Directory containing documents
            sample_size: Number of documents to sample (None = all documents)
            strategy: Sampling strategy ('random', 'sequential', 'stratified')
            seed: Random seed for reproducibility

        Returns:
            List of document file paths
        """
        import random as rand

        if not docs_dir.exists():
            return []

        # Support common document formats
        extensions = [".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"]
        documents = []

        for ext in extensions:
            documents.extend(docs_dir.glob(f"*{ext}"))

        documents = sorted(documents)

        # Apply sampling if requested
        if sample_size is not None and sample_size < len(documents):
            logger.info(f"Sampling {sample_size} documents from {len(documents)} using {strategy} strategy")

            if strategy == "random":
                rand.seed(seed)
                documents = rand.sample(documents, sample_size)
            elif strategy == "sequential":
                documents = documents[:sample_size]
            elif strategy == "stratified":
                # For stratified sampling, we'd need category labels
                # For now, fall back to random sampling
                logger.warning("Stratified sampling not implemented, using random")
                rand.seed(seed)
                documents = rand.sample(documents, sample_size)
            else:
                logger.warning(f"Unknown sampling strategy '{strategy}', using random")
                rand.seed(seed)
                documents = rand.sample(documents, sample_size)

            # Re-sort after sampling for consistency
            documents = sorted(documents)

        return documents

    def _calculate_overall_stats(
        self,
        dataset_results: dict,
        start_time: datetime,
        end_time: datetime,
    ) -> dict:
        """
        Calculate overall statistics across all datasets and parsers.

        Args:
            dataset_results: Results for all datasets
            start_time: Benchmark start time
            end_time: Benchmark end time

        Returns:
            Overall statistics dict
        """
        total_docs = 0
        total_successful = 0
        total_failed = 0
        total_time = (end_time - start_time).total_seconds()

        for dataset_name, dataset_data in dataset_results.items():
            for parser_name, parser_data in dataset_data.get(
                "parsers",
                {},
            ).items():
                agg = parser_data.get("aggregated", {})
                total_docs += agg.get("total_documents", 0)
                total_successful += agg.get("successful_documents", 0)
                total_failed += agg.get("failed_documents", 0)

        return {
            "total_documents": total_docs,
            "total_successful": total_successful,
            "total_failed": total_failed,
            "success_rate": (total_successful / total_docs if total_docs > 0 else 0.0),
            "failure_rate": (total_failed / total_docs if total_docs > 0 else 0.0),
            "total_time": total_time,
            "throughput_docs_per_hour": ((total_docs / total_time) * 3600 if total_time > 0 else 0.0),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        }

    def save_results(
        self,
        results: dict,
        output_file: str | None = None,
    ) -> Path:
        """
        Save benchmark results to JSON file.

        Args:
            results: Results dictionary from run()
            output_file: Output filename (default: timestamp-based)

        Returns:
            Path to saved file
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"benchmark_{timestamp}.json"

        output_path = self.config.output_dir / output_file

        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)

        logger.info(f"Results saved to: {output_path}")
        return output_path

    def load_results(self, results_file: Path) -> dict:
        """
        Load benchmark results from JSON file.

        Args:
            results_file: Path to results file

        Returns:
            Results dictionary
        """
        with open(results_file) as f:
            results = json.load(f)

        logger.info(f"Results loaded from: {results_file}")
        return results
