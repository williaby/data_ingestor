"""Tests for HybridDocumentChunker."""

import logging
import subprocess
import sys
import warnings
from typing import Any

import pytest
from docling_core.transforms.chunker.base import BaseChunk, BaseMeta
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace
from transformers import AutoTokenizer, PreTrainedTokenizerFast

from data_ingestor import chunking
from data_ingestor.chunking import DocumentChunker, HybridDocumentChunker, hybrid_chunker, load_tokenizer
from data_ingestor.conversion import DOCLING_JSON_KEY, docling_json_to_document
from data_ingestor.core.config import Settings
from data_ingestor.core.exceptions import ChunkingError
from data_ingestor.core.models import Document, DocumentFormat
from tests.docling_fixtures import (
    WordTokenizer,
    build_large_table_docling_json,
    build_long_heading_docling_json,
    build_multi_page_section_docling_json,
    build_sample_docling_json,
)

pytestmark = pytest.mark.unit

REQUIRED_METADATA = {
    "document_id",
    "sha256",
    "entity_id",
    "document_type",
    "category",
    "is_confidential",
    "consent_on_file",
    "title",
    "document_date",
    "page_start",
    "page_end",
    "section_title",
}
DOC_META = {
    "sha256": "a" * 64,
    "entity_id": "11111111-1111-1111-1111-111111111111",
    "document_type": "report",
    "category": "Synthetic",
    "is_confidential": False,
    "consent_on_file": True,
    "title": "Synthetic Sample Report",
    "document_date": "2024-01-31",
}


def _document(docling_json: dict[str, Any] | None = None, **meta_overrides: Any) -> Document:
    return docling_json_to_document(
        docling_json or build_sample_docling_json(),
        document_id="doc-1",
        extra_metadata={**DOC_META, **meta_overrides},
    )


def _chunks(max_tokens: int = 64, with_pages: bool = True):
    document = _document(build_sample_docling_json(with_pages=with_pages))
    chunker = HybridDocumentChunker(WordTokenizer(max_tokens=max_tokens))
    return chunker.chunk_document(document), chunker


def test_conforms_to_document_chunker_protocol() -> None:
    chunker: DocumentChunker = HybridDocumentChunker(WordTokenizer())
    assert callable(chunker.chunk_document)


def test_every_chunk_has_a_page() -> None:
    chunks, _ = _chunks()
    assert chunks
    for chunk in chunks:
        assert isinstance(chunk.metadata["page_start"], int)
        assert isinstance(chunk.metadata["page_end"], int)
        assert 1 <= chunk.metadata["page_start"] <= chunk.metadata["page_end"] <= 3
        assert chunk.start_page == chunk.metadata["page_start"]
        assert chunk.end_page == chunk.metadata["page_end"]


def test_chunk_without_page_provenance_is_an_error() -> None:
    document = docling_json_to_document(build_sample_docling_json(with_pages=False), document_id="doc-1")
    chunker = HybridDocumentChunker(WordTokenizer())
    with pytest.raises(ChunkingError):
        chunker.chunk_document(document)


def test_chunks_carry_required_metadata() -> None:
    chunks, _ = _chunks()
    for chunk in chunks:
        assert chunk.metadata.keys() >= REQUIRED_METADATA
        assert chunk.metadata["document_id"] == "doc-1"
        # The consuming application records its own embedding model; the Chunk stage does not
        assert "embedding_model" not in chunk.metadata
        assert "embedded_at" not in chunk.metadata
        assert chunk.metadata["entity_id"] == DOC_META["entity_id"]
        assert chunk.metadata["is_confidential"] is False
        assert chunk.metadata["consent_on_file"] is True
    assert {c.metadata["section_title"] for c in chunks} >= {"Introduction", "Findings"}


def test_chunks_respect_token_cap() -> None:
    chunks, _ = _chunks(max_tokens=64)
    assert len(chunks) > 3  # the long "Findings" paragraph must be split
    assert all(chunk.token_count is not None and chunk.token_count <= 64 for chunk in chunks)


def test_table_survives_in_a_chunk() -> None:
    chunks, _ = _chunks()
    assert any("Widgets" in chunk.content for chunk in chunks)


def test_missing_docling_tree_is_an_error() -> None:
    document = Document(format=DocumentFormat.PDF, metadata=dict(DOC_META))
    chunker = HybridDocumentChunker(WordTokenizer())
    with pytest.raises(ChunkingError, match="no Docling tree"):
        chunker.chunk_document(document)


def test_invalid_docling_tree_is_a_chunking_error_without_document_text() -> None:
    document = Document(
        format=DocumentFormat.PDF,
        metadata={**DOC_META, DOCLING_JSON_KEY: {"schema_name": "SECRET-DOCUMENT-TEXT", "version": 12345}},
    )
    chunker = HybridDocumentChunker(WordTokenizer())
    with pytest.raises(ChunkingError, match="invalid Docling tree") as excinfo:
        chunker.chunk_document(document)
    assert "SECRET-DOCUMENT-TEXT" not in str(excinfo.value)


@pytest.mark.parametrize(
    ("overrides", "named"),
    [
        ({"sha256": None}, "sha256"),
        ({"sha256": ""}, "sha256"),
        ({"entity_id": None}, "entity_id"),
        ({"is_confidential": None}, "is_confidential"),
        ({"is_confidential": "false"}, "is_confidential"),
        ({"consent_on_file": None}, "consent_on_file"),
        ({"consent_on_file": 1}, "consent_on_file"),
    ],
)
def test_missing_or_invalid_document_metadata_is_an_error(overrides: dict[str, Any], named: str) -> None:
    chunker = HybridDocumentChunker(WordTokenizer())
    document = _document(**overrides)
    with pytest.raises(ChunkingError, match=named):
        chunker.chunk_document(document)


@pytest.mark.parametrize("missing", ["sha256", "entity_id", "is_confidential", "consent_on_file"])
def test_absent_required_metadata_key_is_an_error(missing: str) -> None:
    document = _document()
    del document.metadata[missing]
    chunker = HybridDocumentChunker(WordTokenizer())
    with pytest.raises(ChunkingError, match=missing):
        chunker.chunk_document(document)


def test_missing_metadata_error_names_keys_only() -> None:
    document = _document(sha256=None)
    chunker = HybridDocumentChunker(WordTokenizer())
    with pytest.raises(ChunkingError) as excinfo:
        chunker.chunk_document(document)
    assert str(excinfo.value) == "Document doc-1 has missing or invalid metadata: sha256"


def test_large_table_under_a_heading_respects_token_cap() -> None:
    cap = 64
    document = _document(build_large_table_docling_json(rows=40, cols=3, heading_words=7))
    chunks = HybridDocumentChunker(WordTokenizer(max_tokens=cap)).chunk_document(document)

    assert len(chunks) > 1
    assert all(chunk.token_count is not None and chunk.token_count <= cap for chunk in chunks)
    assert all(chunk.content.startswith("head0 head1") for chunk in chunks)  # the heading stays on every part
    assert [c.metadata["chunk_index"] for c in chunks] == list(range(len(chunks)))
    assert all(chunk.metadata["page_start"] == 1 for chunk in chunks)
    cells = "".join(chunk.content for chunk in chunks)
    assert "r39c2" in cells  # no row was lost


def test_chunk_that_cannot_be_brought_under_the_cap_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """If re-splitting keeps producing over-cap text, fail instead of emitting an over-cap chunk."""

    def stubborn_segment(self: HybridChunker, doc_chunk: Any, available_length: int, doc_serializer: Any) -> list[str]:
        return [" ".join(["word"] * 200)]

    monkeypatch.setattr(HybridChunker, "segment", stubborn_segment)
    document = _document(build_large_table_docling_json(rows=40, cols=3, heading_words=7))
    chunker = HybridDocumentChunker(WordTokenizer(max_tokens=64))
    with pytest.raises(ChunkingError, match="cannot be split under"):
        chunker.chunk_document(document)


def test_over_long_heading_is_dropped_and_logged_without_text(caplog: pytest.LogCaptureFixture) -> None:
    document = _document(build_long_heading_docling_json(heading_words=40))
    with caplog.at_level(logging.WARNING, logger="data_ingestor.chunking.hybrid_chunker"):
        chunks = HybridDocumentChunker(WordTokenizer(max_tokens=32)).chunk_document(document)

    assert chunks
    assert all(chunk.token_count is not None and chunk.token_count <= 32 for chunk in chunks)
    assert all(chunk.metadata["section_title"] is None for chunk in chunks)
    assert "lost their headings" in caplog.text
    assert "head0" not in caplog.text  # the chunk text docling quotes is not forwarded


def test_unrelated_warnings_from_the_chunker_are_still_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    def noisy_chunk(self: HybridChunker, dl_doc: Any, **_: Any):
        warnings.warn("something else", UserWarning, stacklevel=1)
        return iter(())

    monkeypatch.setattr(HybridChunker, "chunk", noisy_chunk)
    chunker = HybridDocumentChunker(WordTokenizer())
    document = _document()
    with pytest.warns(UserWarning, match="something else"):
        chunker.chunk_document(document)


def test_unexpected_chunk_type_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def foreign_chunk(self: HybridChunker, dl_doc: Any, **_: Any):
        return iter([BaseChunk(text="x", meta=BaseMeta())])

    monkeypatch.setattr(HybridChunker, "chunk", foreign_chunk)
    chunker = HybridDocumentChunker(WordTokenizer())
    document = _document()
    with pytest.raises(ChunkingError, match="Unexpected chunk type"):
        chunker.chunk_document(document)


def test_split_chunk_reports_the_whole_page_range_of_its_items() -> None:
    """A chunk merged from items on two pages cites both pages."""
    document = _document(build_multi_page_section_docling_json())
    chunks = HybridDocumentChunker(WordTokenizer(max_tokens=128)).chunk_document(document)
    assert len(chunks) == 1
    assert (chunks[0].metadata["page_start"], chunks[0].metadata["page_end"]) == (1, 2)


def _offline_tokenizer() -> PreTrainedTokenizerFast:
    backend = Tokenizer(WordLevel({"[UNK]": 0, "hello": 1, "world": 2}, "[UNK]"))
    backend.pre_tokenizer = Whitespace()
    return PreTrainedTokenizerFast(tokenizer_object=backend)


def test_load_tokenizer_forwards_name_and_revision(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def fake_from_pretrained(name: str, revision: str | None = None) -> PreTrainedTokenizerFast:
        seen.update(name=name, revision=revision)
        return _offline_tokenizer()

    monkeypatch.setattr(AutoTokenizer, "from_pretrained", fake_from_pretrained)

    tokenizer = load_tokenizer("org/model", max_tokens=128, revision="abc123")

    assert seen == {"name": "org/model", "revision": "abc123"}
    assert tokenizer.get_max_tokens() == 128
    assert tokenizer.count_tokens("hello world") == 2


def test_from_settings_builds_a_chunker_with_the_configured_tokenizer(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def fake_from_pretrained(name: str, revision: str | None = None) -> PreTrainedTokenizerFast:
        seen.update(name=name, revision=revision)
        return _offline_tokenizer()

    monkeypatch.setattr(AutoTokenizer, "from_pretrained", fake_from_pretrained)
    settings = Settings(chunk_tokenizer="org/model", chunk_tokenizer_revision="rev1", chunk_max_tokens=64)

    chunker = HybridDocumentChunker.from_settings(settings)

    assert seen == {"name": "org/model", "revision": "rev1"}
    assert chunker._tokenizer.get_max_tokens() == 64


def test_package_exports_are_lazy_but_resolve() -> None:
    assert HybridDocumentChunker is hybrid_chunker.HybridDocumentChunker
    with pytest.raises(AttributeError):
        _ = chunking.does_not_exist


def test_importing_the_package_does_not_load_transformers() -> None:
    code = "import sys, data_ingestor.chunking; sys.exit(1 if 'transformers' in sys.modules else 0)"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, check=False)  # noqa: S603
    assert result.returncode == 0, result.stderr.decode()[-500:]
