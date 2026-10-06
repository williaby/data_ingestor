"""Tests for HybridDocumentChunker."""

import pytest

from data_ingestor.chunking import DocumentChunker, HybridDocumentChunker, load_tokenizer
from data_ingestor.conversion import docling_json_to_document
from data_ingestor.core.exceptions import ChunkingError
from tests.docling_fixtures import WordTokenizer, build_sample_docling_json

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


def _chunks(max_tokens: int = 64, with_pages: bool = True):
    document = docling_json_to_document(
        build_sample_docling_json(with_pages=with_pages),
        document_id="doc-1",
        extra_metadata=DOC_META,
    )
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
    from data_ingestor.core.models import Document, DocumentFormat

    chunker = HybridDocumentChunker(WordTokenizer())
    with pytest.raises(ChunkingError):
        chunker.chunk_document(Document(format=DocumentFormat.PDF))


def test_real_qwen_tokenizer_loads_and_counts() -> None:
    """The default tokenizer is the Qwen3-Embedding one; skip when the hub is unreachable."""
    try:
        tokenizer = load_tokenizer("Qwen/Qwen3-Embedding-0.6B", max_tokens=512)
    except OSError:
        pytest.skip("Hugging Face hub not reachable")
    else:
        assert type(tokenizer.get_tokenizer()).__name__.startswith("Qwen")
        assert tokenizer.count_tokens("hello world") >= 2
        assert tokenizer.get_max_tokens() == 512
