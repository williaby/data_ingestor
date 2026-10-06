"""Tests for chunk-set building, atomic writing and tax-return consent."""

import json
import logging
import uuid
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from data_ingestor.chunking import HybridDocumentChunker
from data_ingestor.cli.main import cli
from data_ingestor.conversion import ConversionResult, docling_json_to_document
from data_ingestor.core.exceptions import ChunkingError
from data_ingestor.core.models import Chunk
from data_ingestor.export import (
    ConsentAction,
    build_chunk_set,
    build_withdrawn_chunk_set,
    is_tax_return,
    reconcile_consent,
    stored_consent,
    write_chunk_set,
)
from tests.docling_fixtures import WordTokenizer, build_sample_docling_json

DOC_ID = "0b1c2d3e-4f50-4a61-8b72-93a4b5c6d7e8"
DOC_META = {
    "sha256": "a" * 64,
    "entity_id": "11111111-1111-1111-1111-111111111111",
    "document_type": "report",
    "category": "Synthetic",
    "is_confidential": False,
    "consent_on_file": False,
    "title": "Synthetic Sample Report",
    "document_date": "2024-01-31",
}
TAX_META = {**DOC_META, "category": "Tax Returns", "document_type": "tax_return", "consent_on_file": True}
CONTRACT_CHUNK_FIELDS = {
    "chunk_id",
    "document_id",
    "trace_id",
    "text",
    "page_range",
    "section_hierarchy",
    "trust_score",
    "ocr_engine_provenance",
    "chunk_strategy",
    "token_count",
    "source_track",
    "hallucination_risk",
}


def _chunks() -> list[Chunk]:
    document = docling_json_to_document(build_sample_docling_json(), document_id=DOC_ID, extra_metadata=DOC_META)
    return HybridDocumentChunker(WordTokenizer(max_tokens=64)).chunk_document(document)


def test_chunk_set_has_contract_shape() -> None:
    chunk_set = build_chunk_set(DOC_ID, _chunks(), "hybrid", document_fields=DOC_META)
    assert chunk_set["schema_version"] == "1.1"
    assert chunk_set["document_id"] == DOC_ID
    assert chunk_set["source_track"] == "document"
    assert chunk_set["total_chunks"] == len(chunk_set["chunks"]) > 3
    uuid.UUID(chunk_set["trace_id"])
    for entry in chunk_set["chunks"]:
        assert entry.keys() >= CONTRACT_CHUNK_FIELDS
        uuid.UUID(entry["chunk_id"])
        assert entry["trace_id"] == chunk_set["trace_id"]
        assert entry["chunk_strategy"] == "hybrid"
        assert len(entry["page_range"]) == 2
        assert 1 <= entry["page_range"][0] <= entry["page_range"][1] <= 3
        assert isinstance(entry["token_count"], int)
        assert isinstance(entry["section_hierarchy"], list)
        assert "audio_fields" not in entry


def test_unscored_fields_are_null() -> None:
    for entry in build_chunk_set(DOC_ID, _chunks(), "hybrid", document_fields=DOC_META)["chunks"]:
        assert entry["trust_score"] is None
        assert entry["ocr_engine_provenance"] is None
        assert entry["hallucination_risk"] is None


def test_chunks_carry_document_fields_and_no_embedding_fields() -> None:
    for entry in build_chunk_set(DOC_ID, _chunks(), "hybrid", document_fields=DOC_META)["chunks"]:
        for key, value in DOC_META.items():
            assert entry[key] == value
        assert "embedding_model" not in entry
        assert "embedded_at" not in entry


def test_section_hierarchy_comes_from_headings() -> None:
    hierarchies = [
        e["section_hierarchy"] for e in build_chunk_set(DOC_ID, _chunks(), "hybrid", document_fields=DOC_META)["chunks"]
    ]
    # the document title is the root of every heading path
    assert ["Synthetic Sample Report", "Introduction"] in hierarchies
    assert ["Synthetic Sample Report", "Findings"] in hierarchies


def test_same_document_gives_identical_chunk_set() -> None:
    first = build_chunk_set(DOC_ID, _chunks(), "hybrid", document_fields=DOC_META)
    second = build_chunk_set(DOC_ID, _chunks(), "hybrid", document_fields=DOC_META)
    assert first == second


def test_explicit_trace_id_is_used() -> None:
    trace = str(uuid.uuid4())
    chunk_set = build_chunk_set(DOC_ID, _chunks(), "hybrid", document_fields=DOC_META, trace_id=trace)
    assert chunk_set["trace_id"] == trace


@pytest.mark.parametrize("bad", ["doc-1", "", "1234"])
def test_non_uuid_document_id_is_an_error(bad: str) -> None:
    with pytest.raises(ChunkingError):
        build_chunk_set(bad, _chunks(), "hybrid", document_fields=DOC_META)


def test_non_uuid_trace_id_is_an_error() -> None:
    with pytest.raises(ChunkingError):
        build_chunk_set(DOC_ID, _chunks(), "hybrid", document_fields=DOC_META, trace_id="nope")


def test_chunk_without_page_fails() -> None:
    with pytest.raises(ChunkingError):
        build_chunk_set(DOC_ID, [Chunk(content="no page")], "hybrid", document_fields=DOC_META)


def test_write_creates_named_file_without_temp_leftovers(tmp_path: Path) -> None:
    chunk_set = build_chunk_set(DOC_ID, _chunks(), "hybrid", document_fields=DOC_META)
    target = write_chunk_set(chunk_set, tmp_path / "chunks")
    assert target == tmp_path / "chunks" / f"{DOC_ID}.json"
    assert json.loads(target.read_text(encoding="utf-8")) == chunk_set
    assert [p.name for p in (tmp_path / "chunks").iterdir()] == [f"{DOC_ID}.json"]
    # null scores serialise as JSON null, not a number or a string
    raw = json.loads(target.read_text(encoding="utf-8"))
    assert raw["chunks"][0]["trust_score"] is None


def test_rewrite_replaces_the_file(tmp_path: Path) -> None:
    chunk_set = build_chunk_set(DOC_ID, _chunks(), "hybrid", document_fields=DOC_META)
    write_chunk_set(chunk_set, tmp_path)
    replaced = {**chunk_set, "chunk_strategy": "token"}
    target = write_chunk_set(replaced, tmp_path)
    assert json.loads(target.read_text(encoding="utf-8"))["chunk_strategy"] == "token"
    assert len(list(tmp_path.iterdir())) == 1


def test_failed_write_leaves_no_partial_file(tmp_path: Path) -> None:
    chunk_set = build_chunk_set(DOC_ID, _chunks(), "hybrid", document_fields=DOC_META)
    write_chunk_set(chunk_set, tmp_path)
    before = (tmp_path / f"{DOC_ID}.json").read_text(encoding="utf-8")
    broken = {**chunk_set, "chunks": [{"text": object()}]}  # not JSON serialisable
    with pytest.raises(TypeError):
        write_chunk_set(broken, tmp_path)
    assert (tmp_path / f"{DOC_ID}.json").read_text(encoding="utf-8") == before
    assert [p.name for p in tmp_path.iterdir()] == [f"{DOC_ID}.json"]


def test_cli_chunk_writes_chunk_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "sample.pdf"
    source.write_bytes(b"%PDF-1.4 synthetic")

    class FakeClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def convert(self, path: Path) -> ConversionResult:
            return ConversionResult(build_sample_docling_json(), "success", path.name)

        def close(self) -> None:
            pass

    monkeypatch.setattr("data_ingestor.conversion.DoclingServeClient", FakeClient)
    monkeypatch.setattr("data_ingestor.chunking.load_tokenizer", lambda _name, max_tokens: WordTokenizer(max_tokens=64))

    out = tmp_path / "out"
    result = CliRunner().invoke(
        cli,
        ["chunk", str(source), "--document-id", DOC_ID, "--output-dir", str(out), "--category", "Synthetic"],
    )
    assert result.exit_code == 0, result.output
    data = json.loads((out / f"{DOC_ID}.json").read_text(encoding="utf-8"))
    assert data["chunks"][0]["category"] == "Synthetic"
    assert len(data["chunks"][0]["sha256"]) == 64
    assert data["chunk_strategy"] == "hybrid"
    # no document store record is read, so consent is never on file
    assert data["consent_on_file"] is False
    assert all(entry["consent_on_file"] is False for entry in data["chunks"])


def test_cli_chunk_rejects_bad_document_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "sample.pdf"
    source.write_bytes(b"%PDF-1.4 synthetic")

    class FakeClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def convert(self, path: Path) -> ConversionResult:
            return ConversionResult(build_sample_docling_json(), "success", path.name)

        def close(self) -> None:
            pass

    monkeypatch.setattr("data_ingestor.conversion.DoclingServeClient", FakeClient)
    monkeypatch.setattr("data_ingestor.chunking.load_tokenizer", lambda _name, max_tokens: WordTokenizer(max_tokens=64))
    result = CliRunner().invoke(
        cli,
        ["chunk", str(source), "--document-id", "doc-1", "--output-dir", str(tmp_path / "o")],
    )
    assert result.exit_code == 1
    assert not (tmp_path / "o").exists()


# --- tax-return consent -------------------------------------------------------


def _write_consented_tax_return(output_dir: Path) -> Path:
    return write_chunk_set(build_chunk_set(DOC_ID, _chunks(), "hybrid", document_fields=TAX_META), output_dir)


@pytest.mark.parametrize("consent", [True, False])
def test_consent_on_file_is_copied_into_every_chunk(consent: bool) -> None:
    chunk_set = build_chunk_set(DOC_ID, _chunks(), "hybrid", document_fields={**DOC_META, "consent_on_file": consent})
    assert chunk_set["chunks"]
    assert chunk_set["consent_on_file"] is consent
    assert all(entry["consent_on_file"] is consent for entry in chunk_set["chunks"])


def test_set_carries_document_fields() -> None:
    chunk_set = build_chunk_set(DOC_ID, _chunks(), "hybrid", document_fields=TAX_META)
    for key, value in TAX_META.items():
        assert chunk_set[key] == value


def test_chunk_metadata_does_not_override_document_consent() -> None:
    chunks = [
        Chunk(content="page one", start_page=1, end_page=1, metadata={"consent_on_file": True}),
        Chunk(content="page two", start_page=2, end_page=2, metadata={"consent_on_file": False}),
    ]
    chunk_set = build_chunk_set(DOC_ID, chunks, "hybrid", document_fields=DOC_META)
    assert [entry["consent_on_file"] for entry in chunk_set["chunks"]] == [False, False]


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        ({}, False),
        ({"consent_on_file": None}, False),
        ({"consent_on_file": "true"}, False),
        ({"consent_on_file": 1}, False),
        ({"consent_on_file": False}, False),
        ({"consent_on_file": True}, True),
    ],
)
def test_consent_is_true_only_when_exactly_true(fields: dict[str, Any], expected: bool) -> None:
    meta = {key: value for key, value in DOC_META.items() if key != "consent_on_file"}
    chunk_set = build_chunk_set(DOC_ID, _chunks(), "hybrid", document_fields={**meta, **fields})
    assert chunk_set["consent_on_file"] is expected
    assert all(entry["consent_on_file"] is expected for entry in chunk_set["chunks"])


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        ({"category": "Tax Returns"}, True),
        ({"category": " tax returns "}, True),
        ({"document_type": "tax_return"}, True),
        ({"document_type": "TAX_ELECTION"}, True),
        ({"category": "Synthetic", "document_type": "report"}, False),
        ({"category": None, "document_type": None}, False),
        ({}, False),
    ],
)
def test_is_tax_return(fields: dict[str, Any], expected: bool) -> None:
    assert is_tax_return(fields) is expected


@pytest.mark.parametrize("consent", [False, None, "true"])
@pytest.mark.parametrize("marker", [{"category": "Tax Returns"}, {"document_type": "tax_return"}])
def test_tax_return_without_consent_is_refused(consent: object, marker: dict[str, str]) -> None:
    fields = {**DOC_META, **marker, "consent_on_file": consent}
    with pytest.raises(ChunkingError, match="consent"):
        build_chunk_set(DOC_ID, _chunks(), "hybrid", document_fields=fields)


def test_tax_return_with_consent_is_chunked() -> None:
    chunk_set = build_chunk_set(DOC_ID, _chunks(), "hybrid", document_fields=TAX_META)
    assert chunk_set["total_chunks"] > 0
    assert all(entry["consent_on_file"] is True for entry in chunk_set["chunks"])


def test_withdrawn_chunk_set_has_no_text_and_no_consent() -> None:
    withdrawn = build_withdrawn_chunk_set(DOC_ID, TAX_META)
    assert withdrawn["consent_on_file"] is False
    assert withdrawn["chunks"] == []
    assert withdrawn["total_chunks"] == 0
    assert withdrawn["schema_version"] == "1.1"
    assert withdrawn["source_track"] == "document"
    uuid.UUID(withdrawn["trace_id"])
    # the document stays recognisable as a tax return, with its hash, so a reader can act on it
    assert withdrawn["category"] == "Tax Returns"
    assert withdrawn["sha256"] == TAX_META["sha256"]
    assert '"text"' not in json.dumps(withdrawn)


def test_stored_consent_reads_the_existing_file(tmp_path: Path) -> None:
    assert stored_consent(tmp_path, DOC_ID) is None
    _write_consented_tax_return(tmp_path)
    assert stored_consent(tmp_path, DOC_ID) is True
    write_chunk_set(build_withdrawn_chunk_set(DOC_ID, TAX_META), tmp_path)
    assert stored_consent(tmp_path, DOC_ID) is False


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        "[]",
        json.dumps({"document_id": DOC_ID, "chunks": []}),
        json.dumps({"document_id": DOC_ID, "chunks": [{"text": "x"}]}),
        json.dumps({"document_id": DOC_ID, "consent_on_file": True, "chunks": [{"consent_on_file": "true"}]}),
    ],
)
def test_stored_consent_fails_closed(tmp_path: Path, content: str) -> None:
    (tmp_path / f"{DOC_ID}.json").write_text(content, encoding="utf-8")
    assert stored_consent(tmp_path, DOC_ID) is False


def test_reconcile_ignores_documents_that_are_not_tax_returns(tmp_path: Path) -> None:
    assert reconcile_consent(DOC_ID, DOC_META, tmp_path) is ConsentAction.NOT_REQUIRED
    assert list(tmp_path.iterdir()) == []


def test_reconcile_skips_unconsented_tax_return_with_no_chunk_set(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="data_ingestor.export.chunk_set")
    fields = {**TAX_META, "consent_on_file": False}
    assert reconcile_consent(DOC_ID, fields, tmp_path) is ConsentAction.SKIP
    assert list(tmp_path.iterdir()) == []
    assert DOC_ID in caplog.text
    # logged by document ID only
    assert TAX_META["title"] not in caplog.text
    assert TAX_META["sha256"] not in caplog.text


def test_reconcile_chunks_a_newly_consented_tax_return(tmp_path: Path) -> None:
    assert reconcile_consent(DOC_ID, TAX_META, tmp_path) is ConsentAction.CHUNK
    _write_consented_tax_return(tmp_path)
    assert reconcile_consent(DOC_ID, TAX_META, tmp_path) is ConsentAction.UNCHANGED


def test_withdrawn_consent_rewrites_the_chunk_set(tmp_path: Path) -> None:
    target = _write_consented_tax_return(tmp_path)
    before = target.read_text(encoding="utf-8")

    withdrawn_fields = {**TAX_META, "consent_on_file": False}
    assert reconcile_consent(DOC_ID, withdrawn_fields, tmp_path) is ConsentAction.WITHDRAWN

    after = target.read_text(encoding="utf-8")
    assert after != before
    data = json.loads(after)
    assert data["document_id"] == DOC_ID
    assert data["consent_on_file"] is False
    assert data["chunks"] == []
    assert data["total_chunks"] == 0
    # the hash is unchanged: only consent changed, and that alone rewrites the file
    assert data["sha256"] == TAX_META["sha256"]
    for chunk in json.loads(before)["chunks"]:
        assert chunk["text"] not in after
    assert [p.name for p in tmp_path.iterdir()] == [f"{DOC_ID}.json"]


def test_withdrawal_is_idempotent(tmp_path: Path) -> None:
    _write_consented_tax_return(tmp_path)
    withdrawn_fields = {**TAX_META, "consent_on_file": False}
    reconcile_consent(DOC_ID, withdrawn_fields, tmp_path)
    target = tmp_path / f"{DOC_ID}.json"
    first = target.read_text(encoding="utf-8")
    first_inode = target.stat().st_ino
    assert reconcile_consent(DOC_ID, withdrawn_fields, tmp_path) is ConsentAction.WITHDRAWN
    assert target.read_text(encoding="utf-8") == first
    assert target.stat().st_ino == first_inode  # not rewritten


def test_corrupt_chunk_set_of_unconsented_tax_return_is_replaced(tmp_path: Path) -> None:
    (tmp_path / f"{DOC_ID}.json").write_text("{broken", encoding="utf-8")
    withdrawn_fields = {**TAX_META, "consent_on_file": False}
    assert reconcile_consent(DOC_ID, withdrawn_fields, tmp_path) is ConsentAction.WITHDRAWN
    assert json.loads((tmp_path / f"{DOC_ID}.json").read_text(encoding="utf-8"))["consent_on_file"] is False


def test_regranted_consent_is_chunked_again(tmp_path: Path) -> None:
    write_chunk_set(build_withdrawn_chunk_set(DOC_ID, TAX_META), tmp_path)
    assert reconcile_consent(DOC_ID, TAX_META, tmp_path) is ConsentAction.CHUNK
    _write_consented_tax_return(tmp_path)
    data = json.loads((tmp_path / f"{DOC_ID}.json").read_text(encoding="utf-8"))
    assert data["consent_on_file"] is True
    assert data["total_chunks"] > 0


def test_reconcile_rejects_bad_document_id(tmp_path: Path) -> None:
    with pytest.raises(ChunkingError):
        reconcile_consent("doc-1", TAX_META, tmp_path)


@pytest.mark.parametrize(
    "flags",
    [["--category", "Tax Returns"], ["--document-type", "tax_return"]],
)
def test_cli_chunk_refuses_tax_return(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, flags: list[str]) -> None:
    source = tmp_path / "sample.pdf"
    source.write_bytes(b"%PDF-1.4 synthetic")

    class FailingClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            raise AssertionError("a tax return must not reach docling-serve")

    monkeypatch.setattr("data_ingestor.conversion.DoclingServeClient", FailingClient)
    out = tmp_path / "out"
    result = CliRunner().invoke(cli, ["chunk", str(source), "--document-id", DOC_ID, "--output-dir", str(out), *flags])
    assert result.exit_code == 1
    assert "consent" in result.output
    assert not out.exists()
