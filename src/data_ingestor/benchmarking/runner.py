"""
Benchmark runner with parallel processing support.

Handles document processing with multiple workers, progress tracking,
and result collection.
"""

import logging
import time
from pathlib import Path

from tqdm import tqdm

from data_ingestor.core.config import Settings
from data_ingestor.core.models import DocumentFormat
from data_ingestor.evaluation.base import BaseEvaluator
from data_ingestor.evaluation.models import EvaluationResult
from data_ingestor.parsers.pdf_parser import MarkerParser, PyMuPDF4LLMParser, PyMuPDFParser
from data_ingestor.pipeline.router import DocumentRouter

logger = logging.getLogger(__name__)


class BenchmarkRunner:
    """
    Runs benchmarks with parallel processing.

    Coordinates parallel document processing, tracks progress, handles
    timeouts and errors, and collects evaluation results.

    Example:
        >>> runner = BenchmarkRunner(workers=4, batch_size=32)
        >>> results = runner.run_batch(
        ...     document_files=pdf_files,
        ...     parser_name="pymupdf",
        ...     evaluator=readoc_evaluator,
        ... )
    """

    def __init__(
        self,
        workers: int = 4,
        batch_size: int = 32,
        timeout: int = 120,
    ) -> None:
        """
        Initialize benchmark runner.

        Args:
            workers: Number of parallel workers
            batch_size: Documents per batch
            timeout: Maximum seconds per document
        """
        self.workers = workers
        self.batch_size = batch_size
        self.timeout = timeout

        # Initialize settings and DocumentRouter
        # #ASSUME: DocumentRouter can be shared across workers
        # #VERIFY: Router is thread-safe or process-safe
        settings = Settings()
        self.settings = settings
        self.workers = workers

        # Store available parsers (don't register yet - will register per benchmark)
        self.available_parsers = {
            "marker": MarkerParser,
            "pymupdf4llm": PyMuPDF4LLMParser,
            "pymupdf": PyMuPDFParser,
        }

        logger.info(f"Benchmark runner initialized with {workers} workers")

    def run_batch(
        self,
        document_files: list[Path],
        parser_name: str,
        evaluator: BaseEvaluator,
    ) -> list[EvaluationResult]:
        """
        Process batch of documents with parallel workers.

        Args:
            document_files: List of document file paths
            parser_name: Parser to use (e.g., "pymupdf", "pymupdf4llm", "marker")
            evaluator: Evaluator instance for this dataset

        Returns:
            List of EvaluationResult objects
        """
        # Create fresh router with ONLY the specified parser
        # #CRITICAL: Each benchmark run must use isolated parser to ensure accurate results
        router = DocumentRouter(self.settings)

        # Register only the requested parser
        if parser_name not in self.available_parsers:
            raise ValueError(
                f"Unknown parser: {parser_name}. Available: {', '.join(self.available_parsers.keys())}",
            )

        parser_class = self.available_parsers[parser_name]
        parser_config = self.settings.get_parser_config(parser_name)

        try:
            parser = parser_class(parser_config)
            router.parser_registry.register(parser, [DocumentFormat.PDF])
            logger.info(f"Registered {parser_class.__name__} for PDF processing")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize {parser_name}: {e}")

        logger.info(f"Processing {len(document_files)} documents...")

        results = []

        # Process in batches for better progress tracking
        # Use single-threaded processing for now (Phase 1.5)
        # Phase 2 will add proper multiprocessing with shared state management
        for doc_file in tqdm(document_files, desc=f"  {parser_name}"):
            result = self._process_document(
                doc_file,
                parser_name,
                evaluator,
                router,
            )
            results.append(result)

        logger.info(f"Completed processing {len(results)} documents")
        return results

    def _process_document(
        self,
        doc_file: Path,
        parser_name: str,
        evaluator: BaseEvaluator,
        router: DocumentRouter,
    ) -> EvaluationResult:
        """
        Process single document with timeout and error handling.

        Args:
            doc_file: Document file path
            parser_name: Parser name
            evaluator: Evaluator instance
            router: DocumentRouter with registered parser

        Returns:
            EvaluationResult
        """
        doc_id = doc_file.stem

        try:
            start_time = time.time()

            # Parse document
            # #CRITICAL: Document parsing may fail or timeout
            # #VERIFY: Errors are caught and logged
            document, parse_result = router.process_document(
                source_path=doc_file,
                source_url=None,
                metadata={"doc_id": doc_id, "parser": parser_name},
            )

            if not document or not parse_result.success:
                raise RuntimeError(
                    f"Parsing failed: {parse_result.error_message}",
                )

            # Load ground truth
            ground_truth = evaluator.load_ground_truth(doc_id)
            if not ground_truth:
                raise ValueError(f"Ground truth not found for {doc_id}")

            # Evaluate
            result = evaluator.evaluate_document(document, ground_truth)
            result.processing_time = time.time() - start_time

            return result

        except Exception as e:
            logger.error(f"Error processing {doc_id}: {e}")

            # Return failure result
            return EvaluationResult(
                document_id=doc_id,
                dataset=evaluator.dataset_name,
                success=False,
                error=str(e),
            )

    def run_batch_parallel(
        self,
        document_files: list[Path],
        parser_name: str,
        evaluator: BaseEvaluator,
    ) -> list[EvaluationResult]:
        """
        Process batch with ProcessPoolExecutor (for Phase 2).

        This is a placeholder for future parallel processing implementation.
        Currently not used due to complexity of sharing DocumentRouter state.

        Args:
            document_files: List of document paths
            parser_name: Parser name
            evaluator: Evaluator instance

        Returns:
            List of EvaluationResult objects

        Note:
            Parallel processing requires:
            1. Serializable evaluator and router
            2. Shared state management
            3. Proper timeout handling
            4. Result collection and ordering
        """
        # #TODO(Phase 2): Implement parallel processing with ProcessPoolExecutor
        # #CRITICAL: Requires careful handling of shared state
        # #VERIFY: All components are picklable for multiprocessing

        logger.warning(
            "Parallel processing not yet implemented. Using sequential processing.",
        )
        return self.run_batch(document_files, parser_name, evaluator)
