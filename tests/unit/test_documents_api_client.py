"""Tests for the document store API client, against an in-process fake service."""

import hashlib
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import pytest

from data_ingestor.core.config import Settings
from data_ingestor.core.exceptions import ConfigurationError
from data_ingestor.sources import (
    TAX_RETURNS_CATEGORY,
    DocumentNotFoundError,
    DocumentRecord,
    DocumentsApiClient,
    DocumentSourceError,
)
from tests.documents_api_fake import (
    API_KEY,
    BASE_URL,
    PDF_BYTES,
    FakeDocumentsApi,
    make_document,
    make_tax_return,
)

T0 = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)


def _client(api: FakeDocumentsApi, **kwargs: Any) -> DocumentsApiClient:
    sleeps: list[float] = kwargs.pop("sleeps", [])
    return DocumentsApiClient(
        BASE_URL,
        kwargs.pop("api_key", API_KEY),
        transport=api.transport,
        sleep=sleeps.append,
        **kwargs,
    )


# --- listing ---------------------------------------------------------------------


def test_list_returns_every_page_oldest_first() -> None:
    docs = [make_document(updated_at=T0 + timedelta(minutes=n)) for n in range(5)]
    api = FakeDocumentsApi(list(reversed(docs)))
    with _client(api, page_size=2) as client:
        records = client.list_documents()
    assert [str(r.id) for r in records] == [d["id"] for d in docs]
    assert [q["page"] for path, q in api.requests if path == "/api/v1/documents"] == ["1", "2", "3"]
    assert all(q["size"] == "2" for _path, q in api.requests)


def test_list_sends_the_api_key_and_no_filter_by_default() -> None:
    api = FakeDocumentsApi([make_document()])
    seen: list[httpx.Request] = []

    def spy(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return api.transport.handle_request(request)

    client = DocumentsApiClient(BASE_URL, API_KEY, transport=httpx.MockTransport(spy), sleep=lambda _s: None)
    with client:
        client.list_documents()
    assert seen[0].headers["X-API-Key"] == API_KEY
    assert "updated_since" not in seen[0].url.params
    assert "category" not in seen[0].url.params


def test_updated_since_is_sent_in_utc() -> None:
    api = FakeDocumentsApi([make_document(updated_at=T0)])
    plus_two = timezone(timedelta(hours=2))
    with _client(api) as client:
        client.list_documents(updated_since=datetime(2026, 3, 1, 14, 0, tzinfo=plus_two))
        client.list_documents(updated_since=datetime(2026, 3, 1, 12, 0))  # naive means UTC
    sent = [q["updated_since"] for _path, q in api.requests]
    assert sent == ["2026-03-01T12:00:00+00:00", "2026-03-01T12:00:00+00:00"]


def test_updated_since_filters_and_category_filters() -> None:
    old = make_document(updated_at=T0 - timedelta(days=1))
    new = make_document(updated_at=T0)
    tax = make_tax_return(consent_on_file=True, updated_at=T0 - timedelta(days=9))
    api = FakeDocumentsApi([old, new, tax])
    with _client(api) as client:
        since = {str(r.id) for r in client.list_documents(updated_since=T0)}
        tax_only = {str(r.id) for r in client.list_documents(category=TAX_RETURNS_CATEGORY)}
    assert since == {new["id"]}
    assert tax_only == {tax["id"]}


def _public(document: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in document.items() if not key.startswith("_")}


def _paged_client(pages: list[list[dict[str, Any]]], *, page_size: int = 1) -> DocumentsApiClient:
    """A client whose service returns the given pages, one per ``page`` query value."""

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        body = {
            "items": [_public(d) for d in pages[page - 1]],
            "total": sum(len(p) for p in pages),
            "page": page,
            "size": page_size,
            "pages": len(pages),
        }
        return httpx.Response(200, json=body)

    return DocumentsApiClient(
        BASE_URL,
        API_KEY,
        transport=httpx.MockTransport(handler),
        sleep=lambda _s: None,
        page_size=page_size,
    )


def test_list_drops_a_record_repeated_across_pages() -> None:
    first = make_document(updated_at=T0)
    second = make_document(updated_at=T0 + timedelta(minutes=1))
    # an edit shifted the first record onto the second page as well
    with _paged_client([[first], [second, first]]) as client:
        records = client.list_documents()
    assert sorted(str(r.id) for r in records) == sorted([first["id"], second["id"]])


def test_list_keeps_the_newest_copy_of_a_repeated_record() -> None:
    doc = make_document(updated_at=T0)
    newer = {**doc, "title": "Edited", "updated_at": (T0 + timedelta(minutes=5)).isoformat()}
    with _paged_client([[doc], [newer]]) as client:
        (record,) = client.list_documents()
    assert record.title == "Edited"


@pytest.mark.parametrize(
    ("status", "needle"),
    [(401, "API key"), (503, "not configured"), (500, "HTTP 500"), (404, "HTTP 404")],
)
def test_list_errors_carry_the_status_and_never_the_body(status: int, needle: str) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"detail": "secret-detail"})

    client = DocumentsApiClient(BASE_URL, API_KEY, transport=httpx.MockTransport(handler), sleep=lambda _s: None)
    with client, pytest.raises(DocumentSourceError) as info:
        client.list_documents()
    assert needle in str(info.value)
    assert str(status) in str(info.value)
    assert "secret-detail" not in str(info.value)


def test_a_wrong_key_is_an_error_without_the_key_in_the_message() -> None:
    api = FakeDocumentsApi([make_document()])
    with _client(api, api_key="wrong-key-value") as client, pytest.raises(DocumentSourceError) as info:
        client.list_documents()
    assert "wrong-key-value" not in str(info.value)
    assert "secret-detail" not in str(info.value)


def test_list_rejects_a_body_that_is_not_a_page() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": True})

    client = DocumentsApiClient(BASE_URL, API_KEY, transport=httpx.MockTransport(handler), sleep=lambda _s: None)
    with client, pytest.raises(DocumentSourceError, match="unexpected"):
        client.list_documents()


def test_list_rejects_non_json() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<html>not json</html>")

    client = DocumentsApiClient(BASE_URL, API_KEY, transport=httpx.MockTransport(handler), sleep=lambda _s: None)
    with client, pytest.raises(DocumentSourceError, match="JSON"):
        client.list_documents()


def test_transport_failure_is_a_source_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    client = DocumentsApiClient(BASE_URL, API_KEY, transport=httpx.MockTransport(handler), sleep=lambda _s: None)
    with client, pytest.raises(DocumentSourceError, match="ConnectError"):
        client.list_documents()


def test_a_page_loop_that_never_ends_is_stopped() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        item = make_document()
        item.pop("_content")
        return httpx.Response(200, json={"items": [item], "total": 10**9, "page": 1, "size": 1, "pages": 10**9})

    client = DocumentsApiClient(BASE_URL, API_KEY, transport=httpx.MockTransport(handler), sleep=lambda _s: None)
    with client, pytest.raises(DocumentSourceError, match="pages"):
        client.list_documents()


# --- records ---------------------------------------------------------------------


def test_a_record_with_a_non_boolean_consent_is_rejected() -> None:
    doc = make_tax_return(consent_on_file=True)
    api = FakeDocumentsApi([doc])
    doc["consent_on_file"] = "true"  # a string must never count as consent
    with _client(api) as client, pytest.raises(DocumentSourceError, match="record"):
        client.list_documents()


def test_record_fields_for_a_chunk_set() -> None:
    doc = make_tax_return(consent_on_file=True)
    record = DocumentRecord.model_validate({k: v for k, v in doc.items() if not k.startswith("_")})
    fields = record.document_fields()
    assert fields == {
        "entity_id": doc["entity_id"],
        "document_type": "tax_return",
        "category": "Tax Returns",
        "is_confidential": True,
        "consent_on_file": True,
        "title": "Synthetic Tax Return",
        "document_date": "2025-06-30",
        "sha256": doc["sha256"],
    }
    assert record.document_fields(sha256="abc")["sha256"] == "abc"


def test_a_record_ignores_fields_it_does_not_know() -> None:
    doc = make_document()
    body = {k: v for k, v in doc.items() if not k.startswith("_")} | {"added_later": 1}
    assert DocumentRecord.model_validate(body).id


# --- detail ----------------------------------------------------------------------


def test_get_document_returns_the_record_or_none() -> None:
    doc = make_document()
    api = FakeDocumentsApi([doc])
    with _client(api) as client:
        record = client.get_document(doc["id"])
        missing = client.get_document("22222222-2222-4222-8222-222222222222")
    assert record is not None
    assert str(record.id) == doc["id"]
    assert missing is None


# --- rate limiting ---------------------------------------------------------------


def test_a_rate_limited_request_waits_for_retry_after_and_retries() -> None:
    api = FakeDocumentsApi([make_document()])
    api.rate_limit_first = 2
    sleeps: list[float] = []
    with _client(api, sleeps=sleeps) as client:
        assert len(client.list_documents()) == 1
    assert sleeps == [1.0, 1.0]


def test_rate_limiting_that_does_not_clear_is_an_error() -> None:
    api = FakeDocumentsApi([make_document()])
    api.rate_limit_first = 100
    with _client(api) as client, pytest.raises(DocumentSourceError, match="429"):
        client.list_documents()


def test_a_huge_retry_after_is_capped() -> None:
    state = {"calls": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        if state["calls"] == 1:
            return httpx.Response(429, headers={"Retry-After": "86400"})
        return httpx.Response(200, json={"items": [], "total": 0, "page": 1, "size": 50, "pages": 1})

    sleeps: list[float] = []
    client = DocumentsApiClient(BASE_URL, API_KEY, transport=httpx.MockTransport(handler), sleep=sleeps.append)
    with client:
        client.list_documents()
    assert sleeps == [60.0]


# --- file download ---------------------------------------------------------------


def test_download_writes_the_file_and_returns_its_hash(tmp_path: Path) -> None:
    doc = make_document()
    api = FakeDocumentsApi([doc])
    with _client(api) as client:
        downloaded = client.download_file(doc["id"], tmp_path)
    assert downloaded.path.parent == tmp_path
    assert downloaded.path.suffix == ".pdf"
    assert downloaded.path.read_bytes() == PDF_BYTES
    assert downloaded.sha256 == hashlib.sha256(PDF_BYTES).hexdigest()
    assert api.file_requests() == [f"/api/v1/documents/{doc['id']}/file"]


@pytest.mark.parametrize(
    ("mime", "suffix"),
    [("application/pdf", ".pdf"), ("image/png", ".png"), ("image/jpeg", ".jpg"), ("text/plain", ".txt")],
)
def test_download_picks_the_extension_from_the_mime_type(tmp_path: Path, mime: str, suffix: str) -> None:
    doc = make_document(mime_type=mime)
    with _client(FakeDocumentsApi([doc])) as client:
        assert client.download_file(doc["id"], tmp_path).path.suffix == suffix


def test_download_of_an_unknown_type_gets_a_neutral_extension(tmp_path: Path) -> None:
    doc = make_document(mime_type="application/x-unknown-thing")
    with _client(FakeDocumentsApi([doc])) as client:
        assert client.download_file(doc["id"], tmp_path).path.suffix == ".bin"


def test_download_of_a_missing_file_is_not_found(tmp_path: Path) -> None:
    doc = make_document()
    api = FakeDocumentsApi([doc])
    api.file_status[doc["id"]] = 404
    with _client(api) as client, pytest.raises(DocumentNotFoundError):
        client.download_file(doc["id"], tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_download_over_the_limit_by_header_is_refused_and_leaves_nothing(tmp_path: Path) -> None:
    doc = make_document(content=b"x" * 100)
    with (
        _client(FakeDocumentsApi([doc]), max_download_bytes=10) as client,
        pytest.raises(DocumentSourceError, match="limit"),
    ):
        client.download_file(doc["id"], tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_download_over_the_limit_while_streaming_is_refused_and_leaves_nothing(tmp_path: Path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"y" * 100, headers={"Content-Type": "application/pdf"})

    client = DocumentsApiClient(
        BASE_URL,
        API_KEY,
        transport=httpx.MockTransport(handler),
        sleep=lambda _s: None,
        max_download_bytes=10,
    )
    with client, pytest.raises(DocumentSourceError, match="limit"):
        client.download_file("33333333-3333-4333-8333-333333333333", tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_download_error_status_is_a_source_error(tmp_path: Path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "secret-detail"})

    client = DocumentsApiClient(BASE_URL, API_KEY, transport=httpx.MockTransport(handler), sleep=lambda _s: None)
    with client, pytest.raises(DocumentSourceError, match="HTTP 500") as info:
        client.download_file("33333333-3333-4333-8333-333333333333", tmp_path)
    assert "secret-detail" not in str(info.value)


def test_download_refuses_an_id_that_is_not_a_uuid(tmp_path: Path) -> None:
    api = FakeDocumentsApi()
    with _client(api) as client, pytest.raises(DocumentSourceError, match="UUID"):
        client.download_file("../../etc/passwd", tmp_path)
    assert api.requests == []


# --- construction from settings --------------------------------------------------


def _settings(monkeypatch: pytest.MonkeyPatch, **env: str) -> Settings:
    for name in (
        "DATA_INGESTOR_LLC_MANAGER_URL",
        "DATA_INGESTOR_LLC_MANAGER_API_KEY",
        "DATA_INGESTOR_LLC_MANAGER_API_KEY_FILE",
    ):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(f"DATA_INGESTOR_{name}", value)
    return Settings()


def test_from_settings_reads_the_key_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    api = FakeDocumentsApi([make_document()])
    settings = _settings(monkeypatch, LLC_MANAGER_URL=BASE_URL, LLC_MANAGER_API_KEY=API_KEY)
    with DocumentsApiClient.from_settings(settings, transport=api.transport) as client:
        assert len(client.list_documents()) == 1


def test_from_settings_reads_the_key_from_a_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    key_file = tmp_path / "api-key"
    key_file.write_text(f"{API_KEY}\n", encoding="utf-8")
    api = FakeDocumentsApi([make_document()])
    settings = _settings(monkeypatch, LLC_MANAGER_URL=BASE_URL, LLC_MANAGER_API_KEY_FILE=str(key_file))
    with DocumentsApiClient.from_settings(settings, transport=api.transport) as client:
        assert len(client.list_documents()) == 1


@pytest.mark.parametrize(
    ("env", "needle"),
    [
        ({}, "LLC_MANAGER_URL"),
        ({"LLC_MANAGER_URL": BASE_URL}, "API key"),
        ({"LLC_MANAGER_URL": "ftp://nope", "LLC_MANAGER_API_KEY": API_KEY}, "http"),
        ({"LLC_MANAGER_URL": "https://", "LLC_MANAGER_API_KEY": API_KEY}, "http"),
    ],
)
def test_from_settings_refuses_incomplete_settings(
    monkeypatch: pytest.MonkeyPatch,
    env: dict[str, str],
    needle: str,
) -> None:
    with pytest.raises(ConfigurationError, match=needle):
        DocumentsApiClient.from_settings(_settings(monkeypatch, **env))


def test_from_settings_refuses_both_a_key_and_a_key_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    key_file = tmp_path / "api-key"
    key_file.write_text(API_KEY, encoding="utf-8")
    settings = _settings(
        monkeypatch,
        LLC_MANAGER_URL=BASE_URL,
        LLC_MANAGER_API_KEY=API_KEY,
        LLC_MANAGER_API_KEY_FILE=str(key_file),
    )
    with pytest.raises(ConfigurationError, match="both"):
        DocumentsApiClient.from_settings(settings)


@pytest.mark.parametrize("content", ["", "   \n", "two\nlines\n"])
def test_from_settings_refuses_a_bad_key_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, content: str) -> None:
    key_file = tmp_path / "api-key"
    key_file.write_text(content, encoding="utf-8")
    settings = _settings(monkeypatch, LLC_MANAGER_URL=BASE_URL, LLC_MANAGER_API_KEY_FILE=str(key_file))
    with pytest.raises(ConfigurationError, match="key file"):
        DocumentsApiClient.from_settings(settings)


def test_from_settings_refuses_an_unreadable_key_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = _settings(monkeypatch, LLC_MANAGER_URL=BASE_URL, LLC_MANAGER_API_KEY_FILE=str(tmp_path / "missing"))
    with pytest.raises(ConfigurationError, match="key file"):
        DocumentsApiClient.from_settings(settings)


def test_the_key_is_not_shown_in_the_settings_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(monkeypatch, LLC_MANAGER_URL=BASE_URL, LLC_MANAGER_API_KEY=API_KEY)
    assert API_KEY not in repr(settings)
