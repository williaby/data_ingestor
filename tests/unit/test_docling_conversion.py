"""Tests for the docling-serve client and the Docling JSON mapper."""

import logging
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from data_ingestor.conversion import DOCLING_JSON_KEY, DoclingServeClient, docling_json_to_document
from data_ingestor.core.config import Settings
from data_ingestor.core.exceptions import ConversionError
from data_ingestor.core.models import DocumentFormat, ElementType, ProcessingStatus
from data_ingestor.export.exporter import DocumentExporter
from tests.docling_fixtures import build_branch_docling_json, build_sample_docling_json

pytestmark = pytest.mark.unit

LEAK_MARKER = "SECRET-DOCUMENT-TEXT"


@pytest.fixture
def pdf_file(tmp_path: Path) -> Path:
    path = tmp_path / "sample.pdf"
    path.write_bytes(b"%PDF-1.4 synthetic")
    return path


def _client(handler: httpx.MockTransport, api_key: str | None = None) -> DoclingServeClient:
    return DoclingServeClient(base_url="http://docling.test", api_key=api_key, transport=handler)


def _ok_transport(status: str = "success") -> httpx.MockTransport:
    return httpx.MockTransport(
        lambda _request: httpx.Response(
            200,
            json={"status": status, "document": {"json_content": build_sample_docling_json()}},
        ),
    )


def test_convert_posts_multipart_and_returns_json(pdf_file: Path) -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["content_type"] = request.headers["content-type"]
        seen["api_key"] = request.headers.get("x-api-key")
        seen["body"] = request.read()
        return httpx.Response(
            200,
            json={"status": "success", "document": {"json_content": build_sample_docling_json()}},
        )

    result = _client(httpx.MockTransport(handler), api_key="test-key").convert(pdf_file)

    assert seen["path"] == "/v1/convert/file"
    assert str(seen["content_type"]).startswith("multipart/form-data")
    assert seen["api_key"] == "test-key"
    body: bytes = seen["body"]
    assert b'name="files"; filename="sample.pdf"' in body
    assert b"%PDF-1.4 synthetic" in body
    for field, value in (
        ("to_formats", "json"),
        ("do_ocr", "true"),
        ("abort_on_error", "false"),
        ("image_export_mode", "placeholder"),
    ):
        assert f'name="{field}"\r\n\r\n{value}\r\n'.encode() in body
    assert result.status == "success"
    assert result.filename == "sample.pdf"
    assert result.docling_json["name"] == "synthetic-sample"


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500, text=LEAK_MARKER),
        httpx.Response(202, json={"status": "success", "note": LEAK_MARKER}),
        httpx.Response(200, text=LEAK_MARKER),
        httpx.Response(200, json=[LEAK_MARKER]),
        httpx.Response(200, json=LEAK_MARKER),
        httpx.Response(200, json={"status": "success", "document": LEAK_MARKER}),
        httpx.Response(200, json={"status": "success", "document": [LEAK_MARKER]}),
        httpx.Response(200, json={"status": LEAK_MARKER, "document": {}}),
        httpx.Response(200, json={"status": "failure", "document": {"json_content": LEAK_MARKER}}),
        httpx.Response(200, json={"status": "success", "document": {"json_content": {}}}),
        httpx.Response(200, json={"status": "success", "document": {"json_content": LEAK_MARKER}}),
    ],
)
def test_convert_raises_conversion_error_without_leaking_response(pdf_file: Path, response: httpx.Response) -> None:
    client = _client(httpx.MockTransport(lambda _request: response))
    with pytest.raises(ConversionError) as excinfo:
        client.convert(pdf_file)
    assert LEAK_MARKER not in str(excinfo.value)
    assert LEAK_MARKER.lower() not in str(excinfo.value).lower()


def test_convert_bounds_the_echoed_service_status(pdf_file: Path) -> None:
    long_status = "x" * 500 + "\nINJECTED"
    client = _client(httpx.MockTransport(lambda _r: httpx.Response(200, json={"status": long_status})))
    with pytest.raises(ConversionError) as excinfo:
        client.convert(pdf_file)
    assert "INJECTED" not in str(excinfo.value)
    assert len(str(excinfo.value)) < 200


def test_convert_wraps_transport_errors(pdf_file: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    client = _client(httpx.MockTransport(handler))
    with pytest.raises(ConversionError, match="request failed"):
        client.convert(pdf_file)


def test_convert_reports_unreadable_file_as_local_error(tmp_path: Path) -> None:
    client = _client(_ok_transport())
    with pytest.raises(ConversionError, match="cannot read"):
        client.convert(tmp_path / "missing.pdf")


def test_convert_rejects_oversized_upload(pdf_file: Path) -> None:
    client = DoclingServeClient(base_url="http://docling.test", transport=_ok_transport(), max_upload_bytes=4)
    with pytest.raises(ConversionError, match="upload limit"):
        client.convert(pdf_file)


def test_partial_success_is_returned_and_logged(pdf_file: Path, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="data_ingestor.conversion.docling_client"):
        result = _client(_ok_transport("partial_success")).convert(pdf_file)
    assert result.status == "partial_success"
    assert "partial success" in caplog.text


def test_context_manager_closes_the_client(pdf_file: Path) -> None:
    with _client(_ok_transport()) as client:
        assert client.convert(pdf_file).status == "success"
    with pytest.raises(RuntimeError):
        client.convert(pdf_file)


@pytest.mark.parametrize("base_url", ["ftp://docling.test", "docling.test", "http://", ""])
def test_client_rejects_non_http_base_urls(base_url: str) -> None:
    with pytest.raises(ValueError, match="base URL"):
        DoclingServeClient(base_url=base_url)


def test_client_warns_when_api_key_travels_over_plain_http(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="data_ingestor.conversion.docling_client"):
        DoclingServeClient(base_url="http://docling.test", api_key="k").close()
        DoclingServeClient(base_url="http://localhost:5001", api_key="k").close()
        DoclingServeClient(base_url="https://docling.test", api_key="k").close()
    assert caplog.text.count("plain http") == 1


def test_from_settings_unwraps_the_secret_key(pdf_file: Path) -> None:
    seen: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["api_key"] = request.headers.get("x-api-key")
        seen["host"] = request.url.host
        return httpx.Response(
            200,
            json={"status": "success", "document": {"json_content": build_sample_docling_json()}},
        )

    settings = Settings(
        docling_serve_url="http://docling.test",
        docling_serve_api_key=SecretStr("from-settings"),
        docling_serve_timeout=12.5,
    )
    with DoclingServeClient.from_settings(settings, transport=httpx.MockTransport(handler)) as client:
        client.convert(pdf_file)
    assert seen == {"api_key": "from-settings", "host": "docling.test"}


def test_mapper_keeps_pages_headings_and_tables() -> None:
    document = docling_json_to_document(build_sample_docling_json(), document_id="doc-1", filename="sample.pdf")

    assert document.document_id == "doc-1"
    assert DOCLING_JSON_KEY in document.metadata
    types = [element.element_type for element in document.elements]
    assert ElementType.TITLE in types
    assert ElementType.TABLE in types
    assert all(element.metadata.page_number in {1, 2, 3} for element in document.elements)

    table = next(e for e in document.elements if e.element_type == ElementType.TABLE)
    assert table.metadata.page_number == 2
    assert "Widgets" in table.content
    assert table.metadata.text_as_html is not None

    finding = next(e for e in document.elements if e.content.startswith("finding0"))
    assert finding.metadata.extra["section_title"] == "Findings"


def test_mapper_rejects_invalid_json() -> None:
    with pytest.raises(ConversionError):
        docling_json_to_document({"not": "docling"}, document_id="doc-1")


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("a.pdf", DocumentFormat.PDF),
        ("A.DOCX", DocumentFormat.DOCX),
        ("page.html", DocumentFormat.HTML),
        ("page.htm", DocumentFormat.HTML),
        ("notes.xyz", DocumentFormat.UNKNOWN),
        (None, DocumentFormat.UNKNOWN),
    ],
)
def test_mapper_derives_format_from_filename(filename: str | None, expected: DocumentFormat) -> None:
    document = docling_json_to_document(build_sample_docling_json(), document_id="d", filename=filename)
    assert document.format == expected


def test_mapper_explicit_format_wins() -> None:
    document = docling_json_to_document(
        build_sample_docling_json(),
        document_id="d",
        filename="a.pdf",
        document_format=DocumentFormat.DOCX,
    )
    assert document.format == DocumentFormat.DOCX


def test_mapper_marks_partial_conversion_for_review() -> None:
    complete = docling_json_to_document(build_sample_docling_json(), document_id="d")
    partial = docling_json_to_document(
        build_sample_docling_json(),
        document_id="d",
        conversion_status="partial_success",
    )
    assert complete.status == ProcessingStatus.COMPLETED
    assert complete.metadata["conversion_status"] == "success"
    assert partial.status == ProcessingStatus.REQUIRES_REVIEW
    assert partial.metadata["conversion_status"] == "partial_success"


def test_mapper_classifies_items_and_skips_pictures_and_blank_text() -> None:
    document = docling_json_to_document(build_branch_docling_json(), document_id="d", filename="b.pdf")
    by_type = {e.element_type: e for e in document.elements}

    assert by_type[ElementType.LIST_ITEM].content == "first bullet"
    assert by_type[ElementType.CODE_SNIPPET].content == "print('hi')"
    assert by_type[ElementType.FORMULA].content == "E = mc^2"
    contents = [e.content for e in document.elements]
    assert all(content.strip() for content in contents)
    assert len(document.elements) == 6  # title, header, list item, code, formula, paragraph


def test_mapper_category_depth_is_the_heading_level() -> None:
    document = docling_json_to_document(build_branch_docling_json(), document_id="d")
    depths = {e.content: e.metadata.category_depth for e in document.elements}
    assert depths["Branch Title"] == 0
    assert depths["Section"] == 3  # the header's own level, not its depth in the tree (1)
    assert depths["print('hi')"] == 2  # non-headings keep their depth in the tree


def test_mapper_normalizes_bottom_left_boxes_to_top_left() -> None:
    document = docling_json_to_document(build_branch_docling_json(), document_id="d")
    flipped = next(e for e in document.elements if e.content == "bottom left paragraph")
    plain = next(e for e in document.elements if e.content == "first bullet")
    # Bottom-left (t=700, b=680) on a 792pt page becomes top-left (t=92, b=112)
    assert flipped.metadata.coordinates == (10.0, 92.0, 200.0, 112.0)
    assert plain.metadata.coordinates == (10.0, 20.0, 200.0, 40.0)


def test_exporters_do_not_write_the_docling_tree() -> None:
    document = docling_json_to_document(
        build_sample_docling_json(),
        document_id="d",
        extra_metadata={"entity_id": "e1"},
    )
    exporter = DocumentExporter()

    as_json = exporter.to_json(document)
    markdown = exporter.to_markdown(document)

    assert DOCLING_JSON_KEY not in as_json["metadata"]
    assert as_json["metadata"]["entity_id"] == "e1"
    assert DOCLING_JSON_KEY not in markdown
    assert "synthetic-sample" not in markdown  # the tree's document name is not in the front matter
    assert DOCLING_JSON_KEY in document.metadata  # the carrier itself is untouched
