"""
Parser configuration testing framework.

Tests different parser configurations (Marker with/without LLM, Docling with/without
TableFormer, etc.) to measure performance trade-offs and optimize routing decisions.
"""

import logging
import time
import tracemalloc
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml

from data_ingestor.core.config import Settings
from data_ingestor.core.models import Document, DocumentFormat
from data_ingestor.parsers.pdf_parser import MarkerParser, PyMuPDF4LLMParser, PyMuPDFParser
from data_ingestor.evaluation.base import BaseEvaluator

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """
    Performance metrics for a single document processing run.

    Tracks time, memory, GPU usage, quality, and cost metrics.
    """

    # Time metrics
    total_time_seconds: float
    time_per_page_seconds: Optional[float]
    preprocessing_time: float
    processing_time: float
    postprocessing_time: float

    # Memory metrics
    peak_memory_mb: float
    average_memory_mb: float
    memory_growth_mb: float

    # GPU metrics (if available)
    gpu_utilization_percent: Optional[float]
    gpu_memory_used_mb: Optional[float]

    # Quality metrics (if evaluator provided)
    text_accuracy_score: Optional[float]
    structure_preservation_score: Optional[float]
    table_accuracy_score: Optional[float]
    overall_quality_score: Optional[float]

    # Cost metrics
    api_calls_count: int
    estimated_cost_usd: float

    # Document metrics
    pages_processed: int
    elements_extracted: int
    errors_encountered: int

    # Success status
    success: bool
    error_message: Optional[str]

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "PerformanceMetrics":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class ConfigurationResult:
    """
    Results from testing a single parser configuration.

    Contains configuration details, metrics for all documents,
    and aggregated statistics.
    """

    parser_type: str
    configuration: Dict[str, Any]
    configuration_name: str
    timestamp: str
    document_results: List[Dict[str, Any]]  # Per-document metrics
    aggregated_metrics: Dict[str, Any]  # Mean, median, p95, etc.

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "ConfigurationResult":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class ConfigSuite:
    """
    Configuration test suite definition.

    Loaded from YAML, defines all parser configurations to test.
    """

    name: str
    description: str
    version: int
    marker_configs: List[Dict[str, Any]]
    docling_configs: List[Dict[str, Any]]
    pymupdf4llm_configs: List[Dict[str, Any]]
    pymupdf_configs: List[Dict[str, Any]]

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "ConfigSuite":
        """Create from dictionary."""
        return cls(
            name=data.get("name", "Unnamed Suite"),
            description=data.get("description", ""),
            version=data.get("version", 1),
            marker_configs=data.get("marker_configs", []),
            docling_configs=data.get("docling_configs", []),
            pymupdf4llm_configs=data.get("pymupdf4llm_configs", []),
            pymupdf_configs=data.get("pymupdf_configs", []),
        )

    @classmethod
    def from_yaml(cls, path: Path) -> "ConfigSuite":
        """Load configuration suite from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)


class ParserConfigurationTester:
    """
    Test different parser configurations and collect performance metrics.

    Systematically tests parser variants (e.g., Marker with/without LLM)
    to measure performance trade-offs and guide routing optimization.

    Args:
        config_suite (ConfigSuite): Configuration suite to test.
        settings (Optional[Settings]): Optional settings instance.

    Example:
        >>> suite = ConfigSuite.from_yaml("config_suite.yaml")
        >>> tester = ParserConfigurationTester(suite)
        >>> results = tester.test_all_configurations(documents)
    """

    def __init__(
        self,
        config_suite: ConfigSuite,
        settings: Optional[Settings] = None,
    ):
        self.config_suite = config_suite
        self.settings = settings or Settings()

        logger.info(f"Configuration tester initialized: {config_suite.name}")
        logger.info(f"  Marker configs: {len(config_suite.marker_configs)}")
        logger.info(f"  Docling configs: {len(config_suite.docling_configs)}")
        logger.info(f"  PyMuPDF4LLM configs: {len(config_suite.pymupdf4llm_configs)}")
        logger.info(f"  PyMuPDF configs: {len(config_suite.pymupdf_configs)}")

    def test_all_configurations(
        self,
        documents: List[Path],
        evaluator: Optional[BaseEvaluator] = None,
    ) -> List[ConfigurationResult]:
        """
        Test all configurations in suite on document set.

        Args:
            documents (List[Path]): List of document paths to process.
            evaluator (Optional[BaseEvaluator]): Optional evaluator for quality metrics.

        Returns:
            List[ConfigurationResult]: List of configuration result objects.
        """
        logger.info(f"Testing {self._count_total_configs()} configurations on {len(documents)} documents")

        results = []

        # Test Marker configurations
        for config in self.config_suite.marker_configs:
            result = self.test_configuration(
                parser_type="marker",
                config=config,
                documents=documents,
                evaluator=evaluator,
            )
            results.append(result)

        # Test Docling configurations
        for config in self.config_suite.docling_configs:
            result = self.test_configuration(
                parser_type="docling",
                config=config,
                documents=documents,
                evaluator=evaluator,
            )
            results.append(result)

        # Test PyMuPDF4LLM configurations
        for config in self.config_suite.pymupdf4llm_configs:
            result = self.test_configuration(
                parser_type="pymupdf4llm",
                config=config,
                documents=documents,
                evaluator=evaluator,
            )
            results.append(result)

        # Test PyMuPDF configurations
        for config in self.config_suite.pymupdf_configs:
            result = self.test_configuration(
                parser_type="pymupdf",
                config=config,
                documents=documents,
                evaluator=evaluator,
            )
            results.append(result)

        logger.info(f"Configuration testing complete: {len(results)} results")
        return results

    def test_configuration(
        self,
        parser_type: str,
        config: Dict[str, Any],
        documents: List[Path],
        evaluator: Optional[BaseEvaluator] = None,
    ) -> ConfigurationResult:
        """
        Test single parser configuration on document set.

        Args:
            parser_type (str): Parser type ("marker", "docling", "pymupdf4llm", "pymupdf").
            config (Dict[str, Any]): Configuration dictionary for parser.
            documents (List[Path]): List of document paths.
            evaluator (Optional[BaseEvaluator]): Optional evaluator for quality metrics.

        Returns:
            ConfigurationResult: Configuration result with all metrics.
        """
        config_name = config.get("name", f"{parser_type}_unnamed")
        logger.info(f"\nTesting configuration: {config_name}")
        logger.info(f"  Parser: {parser_type}")
        logger.info(f"  Config: {config}")

        # Initialize parser with configuration
        parser = self._initialize_parser(parser_type, config)

        # Process all documents
        document_results = []
        for doc_path in documents:
            metrics = self.run_with_metrics(
                parser=parser,
                document=doc_path,
                evaluator=evaluator,
            )
            document_results.append({
                "document_id": doc_path.stem,
                "metrics": metrics.to_dict(),
            })

        # Aggregate metrics
        aggregated = self._aggregate_metrics(document_results)

        result = ConfigurationResult(
            parser_type=parser_type,
            configuration=config,
            configuration_name=config_name,
            timestamp=datetime.now().isoformat(),
            document_results=document_results,
            aggregated_metrics=aggregated,
        )

        logger.info(f"  Completed: {config_name}")
        logger.info(f"    Avg time: {aggregated['mean_total_time']:.2f}s")
        logger.info(f"    Success rate: {aggregated['success_rate']:.1%}")

        return result

    def run_with_metrics(
        self,
        parser: Any,
        document: Path,
        evaluator: Optional[BaseEvaluator] = None,
    ) -> PerformanceMetrics:
        """
        Execute parser on document and collect all metrics.

        Args:
            parser (Any): Parser instance.
            document (Path): Document path.
            evaluator (Optional[BaseEvaluator]): Optional evaluator for quality metrics.

        Returns:
            PerformanceMetrics: Performance metrics for this run.
        """
        doc_id = document.stem

        # Initialize metrics
        success = False
        error_message = None
        pages_processed = 0
        elements_extracted = 0
        errors_encountered = 0

        # Quality metrics (None if no evaluator)
        text_accuracy = None
        structure_preservation = None
        table_accuracy = None
        overall_quality = None

        # GPU metrics (None if no GPU)
        gpu_utilization = None
        gpu_memory_used = None

        # Cost metrics
        api_calls = 0
        estimated_cost = 0.0

        # Start memory tracking
        tracemalloc.start()
        start_memory = tracemalloc.get_traced_memory()[0] / (1024**2)  # MB

        # Start timing
        start_time = time.time()
        preprocessing_time = 0.0
        processing_time = 0.0
        postprocessing_time = 0.0

        try:
            # Pre-processing phase
            pre_start = time.time()
            # #ASSUME: Minimal pre-processing for now
            preprocessing_time = time.time() - pre_start

            # Processing phase
            proc_start = time.time()

            # #CRITICAL: Parser may fail or hang
            # #VERIFY: Timeout and error handling
            parsed_document = parser.parse(str(document))

            if parsed_document and hasattr(parsed_document, "elements"):
                success = True
                elements_extracted = len(parsed_document.elements)

                # Count pages if available
                if hasattr(parsed_document, "page_count"):
                    pages_processed = parsed_document.page_count
                elif hasattr(parsed_document.metadata, "page_count"):
                    pages_processed = parsed_document.metadata.page_count

            processing_time = time.time() - proc_start

            # Post-processing phase
            post_start = time.time()

            # Evaluate quality if evaluator provided
            if evaluator and parsed_document and success:
                try:
                    ground_truth = evaluator.load_ground_truth(doc_id)
                    if ground_truth:
                        eval_result = evaluator.evaluate_document(parsed_document, ground_truth)
                        if hasattr(eval_result, "metrics"):
                            metrics = eval_result.metrics
                            # Extract quality scores
                            text_accuracy = metrics.get("text_accuracy", None)
                            structure_preservation = metrics.get("structure_score", None)
                            table_accuracy = metrics.get("table_accuracy", None)

                            # Calculate overall quality (weighted average)
                            scores = [s for s in [text_accuracy, structure_preservation, table_accuracy] if s is not None]
                            if scores:
                                overall_quality = sum(scores) / len(scores)
                except Exception as e:
                    logger.debug(f"Quality evaluation failed for {doc_id}: {e}")

            postprocessing_time = time.time() - post_start

        except Exception as e:
            error_message = str(e)
            errors_encountered = 1
            logger.error(f"Error processing {doc_id}: {e}")

        # Stop timing and memory tracking
        total_time = time.time() - start_time
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        current_memory_mb = current_memory / (1024**2)
        peak_memory_mb = peak_memory / (1024**2)
        memory_growth_mb = current_memory_mb - start_memory

        # Calculate time per page
        time_per_page = total_time / pages_processed if pages_processed > 0 else None

        # Try to get GPU metrics if available
        gpu_utilization, gpu_memory_used = self._get_gpu_metrics()

        return PerformanceMetrics(
            total_time_seconds=round(total_time, 3),
            time_per_page_seconds=round(time_per_page, 3) if time_per_page else None,
            preprocessing_time=round(preprocessing_time, 3),
            processing_time=round(processing_time, 3),
            postprocessing_time=round(postprocessing_time, 3),
            peak_memory_mb=round(peak_memory_mb, 2),
            average_memory_mb=round(current_memory_mb, 2),
            memory_growth_mb=round(memory_growth_mb, 2),
            gpu_utilization_percent=gpu_utilization,
            gpu_memory_used_mb=gpu_memory_used,
            text_accuracy_score=text_accuracy,
            structure_preservation_score=structure_preservation,
            table_accuracy_score=table_accuracy,
            overall_quality_score=overall_quality,
            api_calls_count=api_calls,
            estimated_cost_usd=estimated_cost,
            pages_processed=pages_processed,
            elements_extracted=elements_extracted,
            errors_encountered=errors_encountered,
            success=success,
            error_message=error_message,
        )

    def _initialize_parser(self, parser_type: str, config: Dict[str, Any]) -> Any:
        """
        Initialize parser with configuration.

        Args:
            parser_type (str): Parser type.
            config (Dict[str, Any]): Configuration dictionary.

        Returns:
            Any: Parser instance.

        Raises:
            NotImplementedError: If parser type is not yet implemented.
            ValueError: If parser type is unknown.
        """
        # Extract just the parser config (remove "name" field)
        parser_config = {k: v for k, v in config.items() if k != "name"}

        if parser_type == "marker":
            return MarkerParser(parser_config)
        elif parser_type == "docling":
            # #TODO: Import DoclingParser when available
            logger.warning("DoclingParser not yet implemented, skipping")
            raise NotImplementedError("DoclingParser not yet available")
        elif parser_type == "pymupdf4llm":
            return PyMuPDF4LLMParser(parser_config)
        elif parser_type == "pymupdf":
            return PyMuPDFParser(parser_config)
        else:
            raise ValueError(f"Unknown parser type: {parser_type}")

    def _get_gpu_metrics(self) -> tuple[Optional[float], Optional[float]]:
        """
        Get current GPU utilization and memory usage.

        Returns:
            tuple[Optional[float], Optional[float]]: Tuple of (utilization_percent, memory_used_mb).
        """
        # #EDGE: GPU metrics may not be available
        # #VERIFY: Graceful fallback to None

        try:
            import torch

            if torch.cuda.is_available():
                utilization = None  # PyTorch doesn't provide utilization directly
                memory_used_mb = torch.cuda.memory_allocated(0) / (1024**2)
                return utilization, round(memory_used_mb, 2)
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"GPU metrics collection failed: {e}")

        return None, None

    def _aggregate_metrics(self, document_results: List[Dict]) -> Dict[str, Any]:
        """
        Aggregate metrics across all documents.

        Args:
            document_results (List[Dict]): List of per-document results.

        Returns:
            Dict[str, Any]: Dictionary with aggregated statistics.
        """
        if not document_results:
            return {}

        # Extract all metrics
        all_metrics = [r["metrics"] for r in document_results]

        # Calculate success rate
        successes = sum(1 for m in all_metrics if m["success"])
        success_rate = successes / len(all_metrics)

        # Aggregate numeric metrics
        def get_values(key: str) -> List[float]:
            """Get all non-None values for a metric key."""
            return [m[key] for m in all_metrics if m[key] is not None]

        def aggregate_stat(key: str) -> Dict[str, float]:
            """Calculate mean, median, p95 for a metric."""
            values = get_values(key)
            if not values:
                return {"mean": 0.0, "median": 0.0, "p95": 0.0}

            sorted_values = sorted(values)
            mean = sum(values) / len(values)
            median = sorted_values[len(sorted_values) // 2]
            p95_idx = int(len(sorted_values) * 0.95)
            p95 = sorted_values[p95_idx] if len(sorted_values) > 1 else sorted_values[0]

            return {
                "mean": round(mean, 3),
                "median": round(median, 3),
                "p95": round(p95, 3),
            }

        # Aggregate time metrics
        time_stats = aggregate_stat("total_time_seconds")
        page_time_stats = aggregate_stat("time_per_page_seconds")

        # Aggregate memory metrics
        memory_stats = aggregate_stat("peak_memory_mb")

        # Aggregate quality metrics (if available)
        quality_stats = aggregate_stat("overall_quality_score")

        return {
            "total_documents": len(document_results),
            "successful_documents": successes,
            "failed_documents": len(all_metrics) - successes,
            "success_rate": round(success_rate, 4),
            "mean_total_time": time_stats["mean"],
            "median_total_time": time_stats["median"],
            "p95_total_time": time_stats["p95"],
            "mean_time_per_page": page_time_stats["mean"],
            "median_time_per_page": page_time_stats["median"],
            "p95_time_per_page": page_time_stats["p95"],
            "mean_peak_memory_mb": memory_stats["mean"],
            "median_peak_memory_mb": memory_stats["median"],
            "p95_peak_memory_mb": memory_stats["p95"],
            "mean_quality_score": quality_stats["mean"],
            "median_quality_score": quality_stats["median"],
            "p95_quality_score": quality_stats["p95"],
        }

    def _count_total_configs(self) -> int:
        """Count total number of configurations in suite."""
        return (
            len(self.config_suite.marker_configs)
            + len(self.config_suite.docling_configs)
            + len(self.config_suite.pymupdf4llm_configs)
            + len(self.config_suite.pymupdf_configs)
        )
