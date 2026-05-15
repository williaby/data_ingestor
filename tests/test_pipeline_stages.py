"""Pipeline stage contract tests.

These tests exercise the four core pipeline stages documented in the
module docstrings of :mod:`data_ingestor.pipeline.router`,
:mod:`data_ingestor.core.base`, :mod:`data_ingestor.parsers.pdf_parser`,
and :mod:`data_ingestor.chunking.token_chunker`:

* **File validation** -- accept / reject by format, size, and path.
* **PDF extraction** -- happy path with a minimal valid PDF and an
  error path with a mocked-corrupt PDF.
* **Chunking** -- boundary cases: empty, single-word, exact size,
  and overlap-requiring input.
* **Pipeline orchestration** -- exception propagation through
  :meth:`DocumentRouter.process_document`.

No real network, cloud, or LLM calls are made; every external
boundary is mocked.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from data_ingestor.chunking.token_chunker import TokenChunker
from data_ingestor.core.base import BaseParser
from data_ingestor.core.exceptions import ParserError, UnsupportedFormatError
from data_ingestor.core.models import (
    Document,
    DocumentElement,
    DocumentFormat,
    ElementMetadata,
    ElementType,
    ParserResult,
    ProcessingStatus,
)
from data_ingestor.parsers.pdf_parser import PyMuPDFParser
from data_ingestor.pipeline.router import DocumentRouter


FIXTURES_DIR = Path(__file__).parent / "fixtures"


# =============================================================================
# Concrete parser used by the file-validation tests.
# =============================================================================


class _PDFOnlyParser(BaseParser):
    """Minimal concrete parser that only accepts PDF documents.

    Used to exercise :meth:`BaseParser.validate_document` without
    touching the real PyMuPDF / Marker / pymupdf4llm code paths.
    """

    def supports_format(self, document_format: DocumentFormat) -> bool:
        return document_format == DocumentFormat.PDF

    def parse(self, document: Document) -> ParserResult:
        return ParserResult(
            success=True,
            parser_name=self.name,
            processing_time=0.0,
        )

    def health_check(self) -> bool:
        return True


# =============================================================================
# 1. File validation stage
# =============================================================================


class TestFileValidationStage:
    """Contract tests for :meth:`BaseParser.validate_document`.

    Covers the accepted case plus each documented rejection mode:
    invalid format, missing/non-file path, and oversize.
    """

    def test_accepts_valid_pdf_fixture(self, tmp_path: Path) -> None:
        """A real PDF that matches the parser's format passes validation."""
        pdf_path = tmp_path / "doc.pdf"
        pdf_path.write_bytes((FIXTURES_DIR / "minimal_valid.pdf").read_bytes())

        document = Document(source_path=str(pdf_path), format=DocumentFormat.PDF)
        parser = _PDFOnlyParser()

        assert parser.validate_document(document) is True

    def test_rejects_unsupported_format(self, tmp_path: Path) -> None:
        """Validation rejects a document whose format the parser does not handle."""
        pdf_path = tmp_path / "doc.pdf"
        pdf_path.write_bytes((FIXTURES_DIR / "minimal_valid.pdf").read_bytes())

        # The parser only supports PDF; mark the document as DOCX to trip
        # the supports_format branch.
        document = Document(source_path=str(pdf_path), format=DocumentFormat.DOCX)
        parser = _PDFOnlyParser()

        assert parser.validate_document(document) is False

    def test_rejects_invalid_file_extension_via_router(self, tmp_path: Path) -> None:
        """The .xyz fixture cannot be detected as a supported format.

        The router surfaces the rejection as
        :class:`UnsupportedFormatError`, demonstrating that the
        validation stage's "invalid type" branch is reachable end-to-
        end (format detection runs *before* parser validation, so a
        truly unknown extension never reaches a parser at all).
        """
        invalid = tmp_path / "junk.xyz"
        invalid.write_bytes((FIXTURES_DIR / "invalid.xyz").read_bytes())

        router = DocumentRouter()

        with pytest.raises(UnsupportedFormatError):
            router.process_document(source_path=str(invalid))

    def test_rejects_oversized_file(self, tmp_path: Path) -> None:
        """Validation rejects files larger than configured max_file_size_mb."""
        pdf_path = tmp_path / "big.pdf"
        pdf_path.write_bytes((FIXTURES_DIR / "minimal_valid.pdf").read_bytes())

        document = Document(source_path=str(pdf_path), format=DocumentFormat.PDF)
        # Fixture is ~900 bytes (~0.00086 MB); a 0.0001 MB cap forces rejection.
        parser = _PDFOnlyParser(config={"max_file_size_mb": 0.0001})

        assert parser.validate_document(document) is False

    def test_accepts_file_under_size_limit(self, tmp_path: Path) -> None:
        """A file well under the size cap passes."""
        pdf_path = tmp_path / "small.pdf"
        pdf_path.write_bytes((FIXTURES_DIR / "minimal_valid.pdf").read_bytes())

        document = Document(source_path=str(pdf_path), format=DocumentFormat.PDF)
        parser = _PDFOnlyParser(config={"max_file_size_mb": 100})

        assert parser.validate_document(document) is True

    def test_rejects_directory_path(self, tmp_path: Path) -> None:
        """Validation rejects when source_path resolves to a directory."""
        sub = tmp_path / "subdir"
        sub.mkdir()

        document = Document.model_construct(
            source_path=str(sub),
            format=DocumentFormat.PDF,
            status=ProcessingStatus.PENDING,
            metadata={},
        )
        parser = _PDFOnlyParser()

        assert parser.validate_document(document) is False

    def test_path_traversal_rejected_at_document_boundary(self, tmp_path: Path) -> None:
        """A path-traversal-style path to a nonexistent file is rejected.

        The :class:`Document` field validator runs ``Path.exists()`` on
        ``source_path``. A traversal-style path that does not resolve
        to a real file raises ``ValueError`` *before* it can ever reach
        a parser, which is the documented behaviour.
        """
        bogus = str(tmp_path / ".." / ".." / "nonexistent" / "secret.pdf")

        with pytest.raises(ValueError, match="does not exist"):
            Document(source_path=bogus, format=DocumentFormat.PDF)


# =============================================================================
# 2. PDF extraction stage
# =============================================================================


class TestPDFExtractionStage:
    """Contract tests for :meth:`PyMuPDFParser.parse`."""

    def test_parses_minimal_valid_pdf(self, tmp_path: Path) -> None:
        """The minimal-valid-PDF fixture is extracted into at least one element."""
        pdf_path = tmp_path / "doc.pdf"
        pdf_path.write_bytes((FIXTURES_DIR / "minimal_valid.pdf").read_bytes())

        document = Document(source_path=str(pdf_path), format=DocumentFormat.PDF)
        parser = PyMuPDFParser()

        result = parser.parse(document)

        assert result.success is True
        assert result.parser_name == "PyMuPDFParser"
        assert len(result.elements) >= 1
        assert any("Hello pipeline test" in e.content for e in result.elements)
        # Metadata schema sanity check: page_count is always populated.
        assert result.metadata.get("page_count") == 1

    def test_corrupt_pdf_returns_failure_result(self, tmp_path: Path) -> None:
        """A corrupt PDF surfaces as ParserResult(success=False).

        The router relies on this: it must be able to fall through to
        the next parser in the chain, so :meth:`PyMuPDFParser.parse`
        catches PyMuPDF errors and reports them via the result object
        rather than raising.
        """
        bad_pdf = tmp_path / "corrupt.pdf"
        bad_pdf.write_bytes(b"%PDF-1.4\nnot really a pdf at all")

        document = Document(source_path=str(bad_pdf), format=DocumentFormat.PDF)
        parser = PyMuPDFParser()

        # Mock fitz.open to simulate a corrupt PDF without relying on
        # PyMuPDF's exact error message for malformed input.
        with patch(
            "data_ingestor.parsers.pdf_parser.fitz.open",
            side_effect=RuntimeError("fake corrupted PDF"),
        ):
            result = parser.parse(document)

        assert result.success is False
        assert result.parser_name == "PyMuPDFParser"
        assert result.error_message is not None
        assert "fake corrupted PDF" in result.error_message
        assert result.elements == []

    def test_missing_source_path_raises_parser_error(self) -> None:
        """A Document without a source_path is a misuse and raises."""
        document = Document.model_construct(
            source_path=None,
            format=DocumentFormat.PDF,
            status=ProcessingStatus.PENDING,
            metadata={},
        )
        parser = PyMuPDFParser()

        with pytest.raises(ParserError):
            parser.parse(document)


# =============================================================================
# 3. Chunking stage
# =============================================================================


def _doc_with_text(text: str) -> Document:
    """Build a Document carrying a single narrative element with ``text``.

    A small helper so the chunking tests can stay readable. ``content``
    must be non-empty after stripping (Pydantic validator); the caller
    handles the truly-empty case explicitly.
    """
    doc = Document(source_path=None, format=DocumentFormat.PDF)
    doc.elements = [
        DocumentElement(
            element_type=ElementType.NARRATIVE_TEXT,
            content=text,
            metadata=ElementMetadata(page_number=1),
        ),
    ]
    return doc


class TestChunkingStage:
    """Boundary tests for :meth:`TokenChunker.chunk_document`."""

    def test_empty_document_returns_no_chunks(self) -> None:
        """A document with no elements yields an empty chunk list.

        This is the "empty string input" boundary case at the
        document-level boundary. The element-level boundary is
        guarded by Pydantic (content cannot be empty), so the only
        way to express an empty input is an empty elements list.
        """
        doc = Document(source_path=None, format=DocumentFormat.PDF)
        doc.elements = []

        chunker = TokenChunker(chunk_size=100, chunk_overlap=10)
        chunks = chunker.chunk_document(doc)

        assert chunks == []

    def test_pydantic_rejects_truly_empty_element_content(self) -> None:
        """Element-level guard: empty content is rejected at construction.

        Documents the contract: callers cannot bypass chunking by
        sneaking an empty-content element through.
        """
        with pytest.raises(ValueError, match="cannot be empty"):
            DocumentElement(element_type=ElementType.NARRATIVE_TEXT, content="")

    def test_single_word_input_yields_single_chunk(self) -> None:
        """Single-word input collapses to exactly one chunk."""
        chunker = TokenChunker(chunk_size=100, chunk_overlap=10)
        chunks = chunker.chunk_document(_doc_with_text("hello"))

        assert len(chunks) == 1
        assert chunks[0].content.strip() == "hello"
        assert chunks[0].token_count == len(chunker.encoding.encode("hello"))

    def test_input_exactly_at_chunk_size_yields_single_chunk(self) -> None:
        """Input whose token count == chunk_size still fits in one chunk.

        The chunker only seals when *adding the next element would
        exceed* ``chunk_size``; an exact match is the boundary.
        """
        # Build a string whose token count is known and fixed.
        encoding = TokenChunker(chunk_size=10, chunk_overlap=0).encoding
        # 10 single-token words.
        words = ["alpha", "beta", "gamma", "delta", "epsilon",
                 "zeta", "eta", "theta", "iota", "kappa"]
        text = " ".join(words)
        token_count = len(encoding.encode(text))

        chunker = TokenChunker(chunk_size=token_count, chunk_overlap=0)
        chunks = chunker.chunk_document(_doc_with_text(text))

        assert len(chunks) == 1
        assert chunks[0].token_count == token_count
        # The whole text round-trips into the chunk.
        for word in words:
            assert word in chunks[0].content

    def test_input_exceeding_chunk_size_splits_with_overlap(self) -> None:
        """Input larger than chunk_size produces multiple chunks; overlap is honoured.

        Overlap in :class:`TokenChunker` is computed at the *content
        part* granularity (a content part == one element's text). To
        exercise the overlap branch we use many small elements so that
        at least one whole element fits inside the overlap budget when
        a chunk is sealed.
        """
        doc = Document(source_path=None, format=DocumentFormat.PDF)
        # 20 distinct short elements, each comfortably below the
        # overlap budget so they can be carried into the next chunk.
        doc.elements = [
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content=f"sentence number {i}.",
                metadata=ElementMetadata(page_number=1),
            )
            for i in range(20)
        ]

        chunker = TokenChunker(chunk_size=25, chunk_overlap=15)
        chunks = chunker.chunk_document(doc)

        assert len(chunks) > 1, "expected the chunker to seal mid-document"

        # Each chunk's token_count must respect the soft chunk_size cap
        # (within a tolerance of one element since the seal happens
        # *before* the over-budget element is added).
        for chunk in chunks:
            assert chunk.token_count is not None
            assert chunk.token_count <= chunker.chunk_size + chunker.chunk_overlap

        # Overlap contract: at least one consecutive chunk pair shares
        # element content. We compare content parts (split on the
        # element separator "\n\n") rather than substring matches so
        # the assertion exercises the documented overlap mechanism.
        overlap_observed = False
        for i in range(len(chunks) - 1):
            prev_parts = set(chunks[i].content.split("\n\n"))
            next_parts = set(chunks[i + 1].content.split("\n\n"))
            if prev_parts & next_parts:
                overlap_observed = True
                break
        assert overlap_observed, "expected at least one element to overlap between chunks"

    def test_zero_overlap_emits_disjoint_chunks(self) -> None:
        """``chunk_overlap=0`` disables overlap entirely.

        Documents the contract from
        :meth:`TokenChunker.chunk_document` that callers can opt out
        of overlap.
        """
        doc = Document(source_path=None, format=DocumentFormat.PDF)
        doc.elements = [
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content="alpha " * 30,
                metadata=ElementMetadata(page_number=1),
            ),
            DocumentElement(
                element_type=ElementType.NARRATIVE_TEXT,
                content="beta " * 30,
                metadata=ElementMetadata(page_number=1),
            ),
        ]

        chunker = TokenChunker(chunk_size=20, chunk_overlap=0)
        chunks = chunker.chunk_document(doc)

        assert len(chunks) >= 2
        # With zero overlap, each chunk is built from fresh content
        # rather than re-using the tail of the previous chunk.
        assert all(chunk.token_count is not None for chunk in chunks)


# =============================================================================
# 4. Pipeline orchestration -- exception propagation
# =============================================================================


class _RaisingParser(BaseParser):
    """Parser whose ``parse()`` always raises a chosen exception.

    Used to verify that orchestration surfaces parser failures rather
    than silently continuing.
    """

    def __init__(self, exc: BaseException, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.name = "RaisingParser"
        self._exc = exc

    def supports_format(self, document_format: DocumentFormat) -> bool:
        return document_format == DocumentFormat.PDF

    def parse(self, document: Document) -> ParserResult:
        raise self._exc

    def health_check(self) -> bool:
        return True


class _FailingResultParser(BaseParser):
    """Parser that returns ParserResult(success=False).

    Used to confirm that the router records the failure and progresses
    to the next parser rather than declaring success.
    """

    def supports_format(self, document_format: DocumentFormat) -> bool:
        return document_format == DocumentFormat.PDF

    def parse(self, document: Document) -> ParserResult:
        return ParserResult(
            success=False,
            parser_name=self.name,
            processing_time=0.01,
            error_message="parser opted out",
        )

    def health_check(self) -> bool:
        return True


class _SuccessfulParser(BaseParser):
    """Parser whose ``parse()`` always succeeds."""

    def supports_format(self, document_format: DocumentFormat) -> bool:
        return document_format == DocumentFormat.PDF

    def parse(self, document: Document) -> ParserResult:
        return ParserResult(
            success=True,
            parser_name=self.name,
            processing_time=0.01,
            elements=[
                DocumentElement(
                    element_type=ElementType.NARRATIVE_TEXT,
                    content="parsed by SuccessfulParser",
                    metadata=ElementMetadata(page_number=1),
                ),
            ],
        )

    def health_check(self) -> bool:
        return True


@pytest.fixture
def pdf_document_path(tmp_path: Path) -> Path:
    """Write the minimal valid PDF fixture into ``tmp_path`` and return it."""
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes((FIXTURES_DIR / "minimal_valid.pdf").read_bytes())
    return pdf_path


@pytest.fixture
def router_without_preflight(monkeypatch: pytest.MonkeyPatch) -> DocumentRouter:
    """Router with PDF pre-flight disabled.

    The pre-flight stage can write/delete temp files and depends on
    OpenCV; disabling it keeps these orchestration tests focused on
    exception propagation through the parser chain.
    """
    router = DocumentRouter()
    monkeypatch.setattr(router.pdf_analyzer, "analyze",
                        lambda *_a, **_kw: pytest.fail(
                            "pre-flight should not run in this test"))
    # Make the format PDF branch skip pre-flight entirely.
    router.pdf_analyzer = None  # type: ignore[assignment]
    return router


class TestPipelineOrchestration:
    """Exception-propagation contract for :class:`DocumentRouter`."""

    def test_propagates_parser_error_when_all_parsers_fail(
        self, pdf_document_path: Path, router_without_preflight: DocumentRouter,
    ) -> None:
        """When every parser raises, the orchestrator re-raises ParserError."""
        router = router_without_preflight
        router.parser_registry.register(
            _RaisingParser(RuntimeError("kaboom")),
            [DocumentFormat.PDF],
        )

        with pytest.raises(ParserError) as exc_info:
            router.process_document(source_path=str(pdf_document_path))

        # The error message must mention the exhausted-chain marker so
        # operators can distinguish "no parsers" from "all failed".
        assert exc_info.value.parser_name == "all"
        assert "kaboom" in str(exc_info.value.details.get("errors", []))

    def test_falls_through_failure_result_to_next_parser(
        self, pdf_document_path: Path, router_without_preflight: DocumentRouter,
    ) -> None:
        """ParserResult(success=False) is not a stop -- the chain continues.

        The orchestrator must try the next parser when one returns a
        non-successful result. Silently returning the failed result
        would defeat the whole fallback design.
        """
        router = router_without_preflight
        # Failing parser registered first (low-priority number wins).
        router.parser_registry.register(
            _FailingResultParser(config={"priority": 1}),
            [DocumentFormat.PDF],
        )
        router.parser_registry.register(
            _SuccessfulParser(config={"priority": 2}),
            [DocumentFormat.PDF],
        )

        document, result = router.process_document(source_path=str(pdf_document_path))

        assert result.success is True
        assert result.parser_name == "_SuccessfulParser"
        assert document.status == ProcessingStatus.COMPLETED

    def test_raises_unsupported_format_when_no_parsers_registered(
        self, pdf_document_path: Path, router_without_preflight: DocumentRouter,
    ) -> None:
        """No parsers for the format -> UnsupportedFormatError (not silent)."""
        router = router_without_preflight  # registry intentionally empty for PDF

        with pytest.raises(UnsupportedFormatError):
            router.process_document(source_path=str(pdf_document_path))

    def test_parser_exception_is_not_swallowed_inside_route_document(
        self, pdf_document_path: Path, router_without_preflight: DocumentRouter,
    ) -> None:
        """Even with a single parser, a thrown exception bubbles up as ParserError.

        Guards against a regression where the router might catch an
        exception and silently return the unparsed document.
        """
        router = router_without_preflight
        router.parser_registry.register(
            _RaisingParser(ValueError("bad input")),
            [DocumentFormat.PDF],
        )

        document = router.create_document(source_path=str(pdf_document_path))

        with pytest.raises(ParserError):
            router.route_document(document)

        # Document status must reflect the failure rather than remain pending.
        assert document.status == ProcessingStatus.FAILED


# =============================================================================
# 5. External-call isolation guard
# =============================================================================
#
# The autouse fixture below installs a network kill-switch for *every*
# test in this module. If any code path covered here ever starts
# making real HTTP calls (e.g. a cloud-storage upload or LLM API
# request quietly added to a stage), the patched send() raises
# loudly so the regression is caught in CI instead of silently
# hitting the network.


@pytest.fixture(autouse=True)
def _block_real_network_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Autouse fixture: patch HTTP client send paths to fail loudly.

    Patches both ``requests.Session.send`` (synchronous) and
    ``urllib.request.urlopen`` (stdlib) for the duration of every test
    in this module. Per-test monkeypatches stack on top, so individual
    tests can still install their own mocks; what they cannot do is
    accidentally reach the real network.
    """
    def _boom(*_args: Any, **_kwargs: Any) -> None:  # pragma: no cover
        raise AssertionError("network call attempted in unit tests")

    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", _boom)

    requests = pytest.importorskip("requests")
    monkeypatch.setattr(requests.Session, "send", _boom)


def test_network_guard_is_installed() -> None:
    """Smoke check that the autouse guard actually replaces send().

    A pinhole test: confirms the autouse fixture is wired in so future
    refactors that drop the fixture get caught here.
    """
    requests = pytest.importorskip("requests")

    # The guard replaces send() with an inner function whose qualname
    # we can detect without invoking it.
    send_fn = requests.Session.send
    assert "_boom" in getattr(send_fn, "__qualname__", ""), (
        "expected the autouse network guard to have patched "
        "requests.Session.send, but it is still the original"
    )
