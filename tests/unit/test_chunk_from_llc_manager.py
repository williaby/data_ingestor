"""Tests for ``chunk --from-llc-manager``: chunk documents listed by the document store API.

The document store is an in-process fake (see tests/documents_api_fake.py) and docling-serve and
the tokenizer are faked as in test_chunk_set.py. All documents and IDs are synthetic.
"""

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
from click.testing import CliRunner, Result

from data_ingestor.cli.main import cli
from data_ingestor.conversion import ConversionResult
from data_ingestor.core.exceptions import ConversionError
from data_ingestor.export import chunk_set as chunk_set_module
from data_ingestor.export import stored_consent
from tests.docling_fixtures import WordTokenizer, build_sample_docling_json
from tests.documents_api_fake import (
    API_KEY,
    BASE_URL,
    FakeDocumentsApi,
    make_document,
    make_tax_return,
)

pytestmark = pytest.mark.unit

T0 = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)
SINCE = (T0 - timedelta(days=1)).isoformat()


# --- harness -------------------------------------------------------------------------


class Pipeline:
    """The faked conversion and tokenizer, recording what was converted."""

    def __init__(self) -> None:
        self.converted: list[str] = []
        self.status = "success"
        self.errors: dict[str, Exception] = {}
        self.on_convert: Callable[[Path], None] | None = None


@pytest.fixture
def pipeline(monkeypatch: pytest.MonkeyPatch) -> Pipeline:
    state = Pipeline()

    class FakeDoclingClient:
        @classmethod
        def from_settings(cls, _settings: object) -> "FakeDoclingClient":
            return cls()

        def __enter__(self) -> "FakeDoclingClient":
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def convert(self, path: Path) -> ConversionResult:
            state.converted.append(path.stem)
            if state.on_convert is not None:
                state.on_convert(path)
            if path.stem in state.errors:
                raise state.errors[path.stem]
            return ConversionResult(build_sample_docling_json(), state.status, path.name)

    def fake_load_tokenizer(_name: str, _max_tokens: int, revision: str | None = None) -> WordTokenizer:
        return WordTokenizer(max_tokens=64)

    monkeypatch.setattr("data_ingestor.conversion.DoclingServeClient", FakeDoclingClient)
    monkeypatch.setattr("data_ingestor.chunking.hybrid_chunker.load_tokenizer", fake_load_tokenizer)
    return state


@pytest.fixture
def scratch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A private temp directory, so a test can check nothing is left behind."""
    directory = tmp_path / "scratch"
    directory.mkdir()
    monkeypatch.setenv("TMPDIR", str(directory))
    monkeypatch.setattr("tempfile.tempdir", None)
    return directory


def use_api(monkeypatch: pytest.MonkeyPatch, api: FakeDocumentsApi) -> None:
    """Route the real client, built from the real settings, to the fake service."""
    monkeypatch.setattr(httpx, "HTTPTransport", lambda **_kwargs: api.transport)
    monkeypatch.setenv("DATA_INGESTOR_LLC_MANAGER_URL", BASE_URL)
    monkeypatch.setenv("DATA_INGESTOR_LLC_MANAGER_API_KEY", API_KEY)


def run(out: Path, *args: str) -> Result:
    return CliRunner().invoke(cli, ["chunk", "--from-llc-manager", "--output-dir", str(out), *args])


def load(out: Path, document_id: str) -> dict[str, Any]:
    return json.loads((out / f"{document_id}.json").read_text(encoding="utf-8"))


def written(out: Path) -> set[str]:
    return {p.stem for p in out.glob("*.json")} if out.exists() else set()


def write_consented_set(out: Path, document: dict[str, Any]) -> None:
    """Chunk a consented tax return once, so a stored chunk set exists."""
    result = run(out)
    assert result.exit_code == 0, result.output
    assert stored_consent(out, document["id"]) is True


# --- listing and chunking --------------------------------------------------------------


def test_every_listed_document_is_downloaded_chunked_and_written(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    first = make_document(title="First Synthetic Agreement", updated_at=T0)
    second = make_document(title="Second Synthetic Agreement", is_confidential=False, updated_at=T0)
    api = FakeDocumentsApi([first, second])
    use_api(monkeypatch, api)
    out = tmp_path / "out"

    result = run(out)

    assert result.exit_code == 0, result.output
    assert written(out) == {first["id"], second["id"]}
    data = load(out, first["id"])
    assert data["document_id"] == first["id"]
    assert data["entity_id"] == first["entity_id"]
    assert data["category"] == "LLCs"
    assert data["document_type"] == "operating_agreement"
    assert data["title"] == "First Synthetic Agreement"
    assert data["document_date"] == "2025-06-30"
    assert data["sha256"] == first["sha256"]
    assert data["is_confidential"] is True
    assert data["consent_on_file"] is False
    assert data["total_chunks"] > 0
    assert load(out, second["id"])["is_confidential"] is False
    assert all(entry["entity_id"] == first["entity_id"] for entry in data["chunks"])
    # titles can be personal; the console shows IDs and counts only
    assert "Synthetic Agreement" not in result.output
    assert "Chunked 2" in result.output


def test_downloaded_files_are_removed_after_each_document(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    api = FakeDocumentsApi([make_document(updated_at=T0), make_document(updated_at=T0)])
    use_api(monkeypatch, api)
    assert run(tmp_path / "out").exit_code == 0
    assert list(scratch.iterdir()) == []


def test_the_file_is_converted_under_its_document_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    doc = make_document(updated_at=T0, title="Name That Must Not Reach The Converter")
    use_api(monkeypatch, FakeDocumentsApi([doc]))
    assert run(tmp_path / "out").exit_code == 0
    assert pipeline.converted == [doc["id"]]


def test_updated_since_limits_which_documents_are_chunked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    old = make_document(updated_at=T0 - timedelta(days=5))
    new = make_document(updated_at=T0)
    api = FakeDocumentsApi([old, new])
    use_api(monkeypatch, api)
    out = tmp_path / "out"

    result = run(out, "--updated-since", SINCE)

    assert result.exit_code == 0, result.output
    assert written(out) == {new["id"]}
    assert api.file_requests() == [f"/api/v1/documents/{new['id']}/file"]
    sent = {q["updated_since"] for path, q in api.requests if "updated_since" in q}
    assert sent == {"2026-02-28T12:00:00+00:00"}


def test_updated_since_accepts_a_plain_date(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    api = FakeDocumentsApi([make_document(updated_at=T0)])
    use_api(monkeypatch, api)
    assert run(tmp_path / "out", "--updated-since", "2026-03-01").exit_code == 0
    assert {q["updated_since"] for _p, q in api.requests if "updated_since" in q} == {"2026-03-01T00:00:00+00:00"}


def test_the_run_reports_the_newest_updated_at_it_saw(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    api = FakeDocumentsApi([make_document(updated_at=T0), make_document(updated_at=T0 + timedelta(hours=1))])
    use_api(monkeypatch, api)
    result = run(tmp_path / "out")
    assert "2026-03-01T13:00:00+00:00" in result.output


def test_the_run_says_the_next_updated_since_must_overlap_the_newest_updated_at(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    # updated_at is the time the service's transaction started, so a row can commit after a later
    # one was listed: a caller that polls with the newest value as it stands would miss it
    use_api(monkeypatch, FakeDocumentsApi([make_document(updated_at=T0)]))
    result = run(tmp_path / "out")
    assert "pass a value at least 5 minutes earlier than this" in result.output


def test_a_run_with_nothing_to_do_succeeds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    use_api(monkeypatch, FakeDocumentsApi())
    result = run(tmp_path / "out")
    assert result.exit_code == 0, result.output
    assert written(tmp_path / "out") == set()
    assert "Newest updated_at listed: none" in result.output
    assert "at least 5 minutes" not in result.output  # no value was listed, so there is nothing to back off from


def test_a_partial_conversion_is_not_written_and_fails_the_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    doc = make_document(updated_at=T0)
    use_api(monkeypatch, FakeDocumentsApi([doc]))
    pipeline.status = "partial_success"
    result = run(tmp_path / "out")
    assert result.exit_code == 1
    assert doc["id"] in result.output
    assert written(tmp_path / "out") == set()


def test_one_failing_document_does_not_stop_the_others(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    bad = make_document(updated_at=T0)
    good = make_document(updated_at=T0 + timedelta(minutes=1))
    use_api(monkeypatch, FakeDocumentsApi([bad, good]))
    pipeline.errors[bad["id"]] = ConversionError("docling-serve returned HTTP 503")
    out = tmp_path / "out"

    result = run(out)

    assert result.exit_code == 1
    assert written(out) == {good["id"]}
    assert bad["id"] in result.output
    assert "HTTP 503" in result.output
    assert list(scratch.iterdir()) == []


def test_a_file_that_changed_since_its_metadata_was_listed_is_not_chunked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    doc = make_document(updated_at=T0, sha256="0" * 64)  # the listed hash is not the file's hash
    use_api(monkeypatch, FakeDocumentsApi([doc]))
    result = run(tmp_path / "out")
    assert result.exit_code == 1
    assert "changed" in result.output
    assert written(tmp_path / "out") == set()
    assert pipeline.converted == []


def test_a_document_without_a_listed_hash_gets_the_hash_of_the_downloaded_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    doc = make_document(updated_at=T0, sha256=None)
    use_api(monkeypatch, FakeDocumentsApi([doc]))
    out = tmp_path / "out"
    assert run(out).exit_code == 0
    assert load(out, doc["id"])["sha256"] == make_document()["sha256"]


def test_a_document_deleted_after_it_was_listed_is_skipped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    gone = make_document(updated_at=T0)
    kept = make_document(updated_at=T0 + timedelta(minutes=1))
    api = FakeDocumentsApi([gone, kept])

    def delete_gone(document_id: str) -> None:
        if document_id == gone["id"]:
            del api.documents[document_id]

    api.before_detail = delete_gone
    use_api(monkeypatch, api)
    out = tmp_path / "out"
    result = run(out)
    assert result.exit_code == 0, result.output
    assert written(out) == {kept["id"]}


def test_a_document_with_a_missing_file_fails_the_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    doc = make_document(updated_at=T0)
    api = FakeDocumentsApi([doc])
    api.file_status[doc["id"]] = 404
    use_api(monkeypatch, api)
    result = run(tmp_path / "out")
    assert result.exit_code == 1
    assert doc["id"] in result.output
    assert written(tmp_path / "out") == set()


# --- consent: every Tax Returns document, every run --------------------------------------


def test_a_tax_return_with_consent_is_chunked_with_consent_on_every_chunk(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    doc = make_tax_return(consent_on_file=True, updated_at=T0)
    use_api(monkeypatch, FakeDocumentsApi([doc]))
    out = tmp_path / "out"
    assert run(out).exit_code == 0
    data = load(out, doc["id"])
    assert data["consent_on_file"] is True
    assert data["total_chunks"] > 0
    assert all(entry["consent_on_file"] is True for entry in data["chunks"])


def test_a_tax_return_without_consent_is_never_downloaded_or_converted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    doc = make_tax_return(consent_on_file=False, updated_at=T0)
    api = FakeDocumentsApi([doc])
    use_api(monkeypatch, api)
    out = tmp_path / "out"
    result = run(out)
    assert result.exit_code == 0, result.output
    assert api.file_requests() == []
    assert pipeline.converted == []
    assert written(out) == set()


@pytest.mark.parametrize(
    ("category", "document_type"),
    [("Other", "tax_return"), ("Tax Returns", "other"), ("Other", "tax_election")],
)
def test_a_document_labelled_as_a_tax_return_by_type_or_category_needs_consent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
    category: str,
    document_type: str,
) -> None:
    doc = make_document(category=category, document_type=document_type, consent_on_file=False, updated_at=T0)
    api = FakeDocumentsApi([doc])
    use_api(monkeypatch, api)
    assert run(tmp_path / "out").exit_code == 0
    assert api.file_requests() == []
    assert written(tmp_path / "out") == set()


def test_consent_withdrawn_rewrites_the_chunk_set_without_text_even_when_not_updated_since(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    doc = make_tax_return(consent_on_file=True, updated_at=T0 - timedelta(days=30))
    api = FakeDocumentsApi([doc])
    use_api(monkeypatch, api)
    out = tmp_path / "out"
    write_consented_set(out, doc)
    assert load(out, doc["id"])["total_chunks"] > 0

    # consent is withdrawn without the document counting as updated since the watermark
    api.set_consent(doc["id"], False)
    api.requests.clear()
    result = run(out, "--updated-since", SINCE)

    assert result.exit_code == 0, result.output
    data = load(out, doc["id"])
    assert data["consent_on_file"] is False
    assert data["chunks"] == []
    assert data["total_chunks"] == 0
    assert stored_consent(out, doc["id"]) is False
    assert api.file_requests() == []
    # the run asked for the Tax Returns category without the watermark
    sweep = [q for path, q in api.requests if path == "/api/v1/documents" and q.get("category") == "Tax Returns"]
    assert sweep
    assert all("updated_since" not in q for q in sweep)


def test_consent_withdrawn_for_a_document_that_is_in_the_updated_listing_too(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    doc = make_tax_return(consent_on_file=True, updated_at=T0)
    api = FakeDocumentsApi([doc])
    use_api(monkeypatch, api)
    out = tmp_path / "out"
    write_consented_set(out, doc)
    api.set_consent(doc["id"], False)
    pipeline.converted.clear()

    assert run(out).exit_code == 0
    assert load(out, doc["id"])["chunks"] == []
    assert pipeline.converted == []


def test_a_consented_tax_return_that_is_unchanged_and_not_updated_is_left_alone(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    doc = make_tax_return(consent_on_file=True, updated_at=T0 - timedelta(days=30))
    api = FakeDocumentsApi([doc])
    use_api(monkeypatch, api)
    out = tmp_path / "out"
    write_consented_set(out, doc)
    before = (out / f"{doc['id']}.json").read_bytes()
    pipeline.converted.clear()
    api.requests.clear()

    assert run(out, "--updated-since", SINCE).exit_code == 0

    assert pipeline.converted == []
    assert api.file_requests() == []
    assert (out / f"{doc['id']}.json").read_bytes() == before


def test_a_consented_tax_return_in_the_updated_listing_is_chunked_again(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    doc = make_tax_return(consent_on_file=True, updated_at=T0)
    use_api(monkeypatch, FakeDocumentsApi([doc]))
    out = tmp_path / "out"
    write_consented_set(out, doc)
    pipeline.converted.clear()
    assert run(out, "--updated-since", SINCE).exit_code == 0
    assert pipeline.converted == [doc["id"]]


def test_newly_given_consent_is_chunked_even_when_not_updated_since(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    doc = make_tax_return(consent_on_file=True, updated_at=T0 - timedelta(days=30))
    use_api(monkeypatch, FakeDocumentsApi([doc]))
    out = tmp_path / "out"
    assert run(out, "--updated-since", SINCE).exit_code == 0
    assert stored_consent(out, doc["id"]) is True


def test_consent_withdrawn_between_the_listing_and_the_detail_check_stops_the_chunking(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    doc = make_tax_return(consent_on_file=True, updated_at=T0)
    api = FakeDocumentsApi([doc])
    use_api(monkeypatch, api)
    out = tmp_path / "out"
    write_consented_set(out, doc)
    pipeline.converted.clear()
    api.before_detail = lambda document_id: api.set_consent(document_id, False)

    assert run(out).exit_code == 0

    assert pipeline.converted == []
    assert load(out, doc["id"])["chunks"] == []


def test_consent_withdrawn_while_the_document_is_converting_is_not_written(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    doc = make_tax_return(consent_on_file=True, updated_at=T0)
    api = FakeDocumentsApi([doc])
    use_api(monkeypatch, api)
    out = tmp_path / "out"
    write_consented_set(out, doc)
    # the next run converts it again, and consent is withdrawn during the conversion
    pipeline.on_convert = lambda _path: api.set_consent(doc["id"], False)

    result = run(out)

    assert result.exit_code == 0, result.output
    data = load(out, doc["id"])
    assert data["consent_on_file"] is False
    assert data["chunks"] == []


def test_consent_withdrawn_while_converting_a_first_chunk_set_leaves_no_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    doc = make_tax_return(consent_on_file=True, updated_at=T0)
    api = FakeDocumentsApi([doc])
    use_api(monkeypatch, api)
    pipeline.on_convert = lambda _path: api.set_consent(doc["id"], False)
    out = tmp_path / "out"
    assert run(out).exit_code == 0
    assert written(out) == set()


def test_a_failed_withdrawal_write_fails_the_run_and_the_others_still_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    taxed = make_tax_return(consent_on_file=True, updated_at=T0 - timedelta(days=30))
    other = make_document(updated_at=T0)
    api = FakeDocumentsApi([taxed, other])
    use_api(monkeypatch, api)
    out = tmp_path / "out"
    write_consented_set(out, taxed)
    api.set_consent(taxed["id"], False)

    def failing_write(*_args: object, **_kwargs: object) -> Path:
        msg = "disk full"
        raise OSError(msg)

    monkeypatch.setattr(chunk_set_module, "write_chunk_set", failing_write)
    result = run(out, "--updated-since", SINCE)

    assert result.exit_code == 1
    assert taxed["id"] in result.output
    assert "withdrawal" in result.output
    # the stored set still holds text, so the failure must be loud
    assert stored_consent(out, taxed["id"]) is True
    assert other["id"] in written(out)


# --- deleted tax returns ------------------------------------------------------------------


def secret_text_gone(out: Path, document_id: str) -> None:
    data = load(out, document_id)
    assert data["chunks"] == []
    assert data["total_chunks"] == 0
    assert data["consent_on_file"] is False
    assert stored_consent(out, document_id) is False


def test_a_deleted_tax_return_loses_its_stored_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    doc = make_tax_return(consent_on_file=True, updated_at=T0 - timedelta(days=30))
    api = FakeDocumentsApi([doc])
    use_api(monkeypatch, api)
    out = tmp_path / "out"
    write_consented_set(out, doc)
    assert load(out, doc["id"])["total_chunks"] > 0

    api.delete(doc["id"])
    api.requests.clear()
    pipeline.converted.clear()
    result = run(out, "--updated-since", SINCE)

    assert result.exit_code == 0, result.output
    secret_text_gone(out, doc["id"])
    assert load(out, doc["id"])["category"] == "Tax Returns"
    assert api.file_requests() == []
    assert pipeline.converted == []
    assert "withdrawn 1" in result.output


def test_a_deleted_tax_return_filed_under_another_category_loses_its_stored_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    doc = make_document(category="Other", document_type="tax_return", consent_on_file=True, updated_at=T0)
    api = FakeDocumentsApi([doc])
    use_api(monkeypatch, api)
    out = tmp_path / "out"
    write_consented_set(out, doc)
    api.delete(doc["id"])

    assert run(out, "--updated-since", SINCE).exit_code == 0
    secret_text_gone(out, doc["id"])


def test_a_stored_tax_return_missing_from_the_category_listing_is_still_reconciled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    doc = make_document(
        category="Other",
        document_type="tax_return",
        consent_on_file=True,
        updated_at=T0 - timedelta(days=30),
    )
    api = FakeDocumentsApi([doc])
    use_api(monkeypatch, api)
    out = tmp_path / "out"
    write_consented_set(out, doc)
    api.set_consent(doc["id"], False)
    api.requests.clear()

    assert run(out, "--updated-since", SINCE).exit_code == 0

    secret_text_gone(out, doc["id"])
    assert f"/api/v1/documents/{doc['id']}" in api.paths()
    assert api.file_requests() == []


def test_a_stored_tax_return_that_still_exists_and_has_consent_is_left_alone(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    doc = make_document(
        category="Other",
        document_type="tax_return",
        consent_on_file=True,
        updated_at=T0 - timedelta(days=30),
    )
    use_api(monkeypatch, FakeDocumentsApi([doc]))
    out = tmp_path / "out"
    write_consented_set(out, doc)
    before = (out / f"{doc['id']}.json").read_bytes()
    pipeline.converted.clear()

    assert run(out, "--updated-since", SINCE).exit_code == 0

    assert (out / f"{doc['id']}.json").read_bytes() == before
    assert pipeline.converted == []


def test_the_stored_set_of_a_deleted_document_that_is_not_a_tax_return_is_left_alone(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    doc = make_document(updated_at=T0)
    api = FakeDocumentsApi([doc])
    use_api(monkeypatch, api)
    out = tmp_path / "out"
    assert run(out).exit_code == 0
    before = (out / f"{doc['id']}.json").read_bytes()
    api.delete(doc["id"])
    api.requests.clear()

    assert run(out, "--updated-since", SINCE).exit_code == 0

    assert (out / f"{doc['id']}.json").read_bytes() == before
    assert f"/api/v1/documents/{doc['id']}" not in api.paths()


def test_a_tax_return_deleted_after_it_was_listed_loses_its_stored_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    doc = make_tax_return(consent_on_file=True, updated_at=T0)
    api = FakeDocumentsApi([doc])
    use_api(monkeypatch, api)
    out = tmp_path / "out"
    write_consented_set(out, doc)
    pipeline.converted.clear()
    api.before_detail = api.delete

    result = run(out)

    assert result.exit_code == 0, result.output
    secret_text_gone(out, doc["id"])
    assert pipeline.converted == []


def test_a_tax_return_deleted_while_it_converts_is_not_rewritten_with_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    doc = make_tax_return(consent_on_file=True, updated_at=T0)
    api = FakeDocumentsApi([doc])
    use_api(monkeypatch, api)
    out = tmp_path / "out"
    write_consented_set(out, doc)
    pipeline.on_convert = lambda _path: api.delete(doc["id"])

    assert run(out).exit_code == 0

    secret_text_gone(out, doc["id"])


def test_a_tax_return_deleted_before_its_first_chunking_writes_nothing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    doc = make_tax_return(consent_on_file=True, updated_at=T0)
    api = FakeDocumentsApi([doc])
    use_api(monkeypatch, api)
    api.before_detail = api.delete
    out = tmp_path / "out"
    assert run(out).exit_code == 0
    assert written(out) == set()


def test_a_failed_write_for_a_deleted_tax_return_fails_the_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    doc = make_tax_return(consent_on_file=True, updated_at=T0 - timedelta(days=30))
    api = FakeDocumentsApi([doc])
    use_api(monkeypatch, api)
    out = tmp_path / "out"
    write_consented_set(out, doc)
    api.delete(doc["id"])

    def failing_write(*_args: object, **_kwargs: object) -> Path:
        msg = "disk full"
        raise OSError(msg)

    monkeypatch.setattr(chunk_set_module, "write_chunk_set", failing_write)
    result = run(out, "--updated-since", SINCE)

    assert result.exit_code == 1
    assert doc["id"] in result.output
    assert stored_consent(out, doc["id"]) is True


def test_a_stored_set_that_cannot_be_read_fails_the_run_and_is_retried_not_blanked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    doc = make_tax_return(consent_on_file=True, updated_at=T0 - timedelta(days=30))
    api = FakeDocumentsApi([doc])
    use_api(monkeypatch, api)
    out = tmp_path / "out"
    write_consented_set(out, doc)
    api.delete(doc["id"])
    before = (out / f"{doc['id']}.json").read_bytes()

    real_read_text = Path.read_text

    def flaky_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self.name == f"{doc['id']}.json":
            msg = "input/output error"
            raise OSError(msg)
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", flaky_read_text)
    failed = run(out, "--updated-since", SINCE)

    assert failed.exit_code == 1
    assert doc["id"] in failed.output
    assert (out / f"{doc['id']}.json").read_bytes() == before

    monkeypatch.setattr(Path, "read_text", real_read_text)
    retried = run(out, "--updated-since", SINCE)

    assert retried.exit_code == 0, retried.output
    secret_text_gone(out, doc["id"])


def test_a_stored_tax_return_the_api_cannot_check_fails_the_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    doc = make_document(
        category="Other",
        document_type="tax_return",
        consent_on_file=True,
        updated_at=T0 - timedelta(days=30),
    )
    api = FakeDocumentsApi([doc])
    use_api(monkeypatch, api)
    out = tmp_path / "out"
    write_consented_set(out, doc)
    api.detail_status[doc["id"]] = 500

    result = run(out, "--updated-since", SINCE)

    assert result.exit_code == 1
    assert doc["id"] in result.output
    assert "HTTP 500" in result.output
    assert stored_consent(out, doc["id"]) is True


# --- configuration, options and API errors ---------------------------------------------


def test_missing_settings_fail_without_a_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
) -> None:
    monkeypatch.delenv("DATA_INGESTOR_LLC_MANAGER_URL", raising=False)
    monkeypatch.delenv("DATA_INGESTOR_LLC_MANAGER_API_KEY", raising=False)
    result = run(tmp_path / "out")
    assert result.exit_code == 1
    assert "LLC_MANAGER_URL" in result.output
    assert "Traceback" not in result.output
    assert not (tmp_path / "out").exists()


def test_a_rejected_key_fails_the_run_before_anything_is_written(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    api = FakeDocumentsApi([make_document(updated_at=T0)], api_key="a-different-key")
    use_api(monkeypatch, api)
    result = run(tmp_path / "out")
    assert result.exit_code == 1
    assert "API key" in result.output
    assert API_KEY not in result.output
    assert "secret-detail" not in result.output
    assert not (tmp_path / "out").exists()


def test_the_key_file_setting_is_used(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    scratch: Path,
) -> None:
    key_file = tmp_path / "key"
    key_file.write_text(API_KEY + "\n", encoding="utf-8")
    doc = make_document(updated_at=T0)
    use_api(monkeypatch, FakeDocumentsApi([doc]))
    monkeypatch.delenv("DATA_INGESTOR_LLC_MANAGER_API_KEY")
    monkeypatch.setenv("DATA_INGESTOR_LLC_MANAGER_API_KEY_FILE", str(key_file))
    out = tmp_path / "out"
    assert run(out).exit_code == 0
    assert written(out) == {doc["id"]}


@pytest.mark.parametrize(
    "extra",
    [
        ["SAMPLE_FILE"],
        ["--document-id", "0b1c2d3e-4f50-4a61-8b72-93a4b5c6d7e8"],
        ["--entity-id", "11111111-1111-4111-8111-111111111111"],
        ["--category", "Synthetic"],
        ["--document-type", "will"],
        ["--title", "Made Up"],
        ["--document-date", "2024-01-31"],
        ["--trace-id", "0b1c2d3e-4f50-4a61-8b72-93a4b5c6d7e8"],
        ["--not-confidential"],
        ["--confidential"],
    ],
)
def test_single_file_options_are_refused_with_from_llc_manager(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    extra: list[str],
) -> None:
    sample = tmp_path / "sample.pdf"
    sample.write_bytes(b"%PDF-1.4 synthetic")
    api = FakeDocumentsApi([make_document(updated_at=T0)])
    use_api(monkeypatch, api)
    result = run(tmp_path / "out", *[str(sample) if arg == "SAMPLE_FILE" else arg for arg in extra])
    assert result.exit_code == 2
    assert "--from-llc-manager" in result.output
    assert api.requests == []


@pytest.mark.parametrize("value", ["yesterday", "2026-13-01", "2026-03-01T25:00:00", ""])
def test_a_bad_updated_since_is_a_usage_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pipeline: Pipeline,
    value: str,
) -> None:
    api = FakeDocumentsApi()
    use_api(monkeypatch, api)
    result = run(tmp_path / "out", "--updated-since", value)
    assert result.exit_code == 2
    assert "updated-since" in result.output
    assert api.requests == []


def test_updated_since_needs_from_llc_manager(tmp_path: Path, pipeline: Pipeline) -> None:
    source = tmp_path / "sample.pdf"
    source.write_bytes(b"%PDF-1.4 synthetic")
    result = CliRunner().invoke(
        cli,
        [
            "chunk",
            str(source),
            "--document-id",
            "0b1c2d3e-4f50-4a61-8b72-93a4b5c6d7e8",
            "--entity-id",
            "11111111-1111-4111-8111-111111111111",
            "--updated-since",
            SINCE,
        ],
    )
    assert result.exit_code == 2
    assert "--from-llc-manager" in result.output


def test_without_the_flag_a_file_is_still_required(pipeline: Pipeline) -> None:
    result = CliRunner().invoke(cli, ["chunk"])
    assert result.exit_code == 2
    assert "FILE_PATH" in result.output


def test_without_the_flag_the_document_id_is_still_required(tmp_path: Path, pipeline: Pipeline) -> None:
    source = tmp_path / "sample.pdf"
    source.write_bytes(b"%PDF-1.4 synthetic")
    result = CliRunner().invoke(
        cli,
        ["chunk", str(source), "--entity-id", "11111111-1111-4111-8111-111111111111"],
    )
    assert result.exit_code == 2
    assert "document-id" in result.output
