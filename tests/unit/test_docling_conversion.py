"""Tests for the docling-serve client and the Docling JSON mapper."""

from pathlib import Path

import httpx
import pytest

from data_ingestor.conversion import DOCLING_JSON_KEY, DoclingServeClient, docling_json_to_document
from data_ingestor.core.exceptions import ConversionError
from data_ingestor.core.models import ElementType
from tests.docling_fixtures import build_sample_docling_json


@pytest.fixture
def pdf_file(tmp_path: Path) -> Path:
    path = tmp_path / "sample.pdf"
    path.write_bytes(b"%PDF-1.4 synthetic")
    return path


def _client(handler: httpx.MockTransport, api_key: str | None = None) -> DoclingServeClient:
    return DoclingServeClient(base_url="http://docling.test", api_key=api_key, transport=handler)


def test_convert_posts_multipart_and_returns_json(pdf_file: Path) -> None:
    seen: dict[str, object] = {}

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
    assert b'name="to_formats"' in seen["body"]  # type: ignore[operator]
    assert result.status == "success"
    assert result.docling_json["name"] == "synthetic-sample"


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500, text="boom"),
        httpx.Response(200, text="not json"),
        httpx.Response(200, json={"status": "failure", "document": {}}),
        httpx.Response(200, json={"status": "success", "document": {"json_content": {}}}),
    ],
)
def test_convert_raises_conversion_error(pdf_file: Path, response: httpx.Response) -> None:
    client = _client(httpx.MockTransport(lambda _request: response))
    with pytest.raises(ConversionError) as excinfo:
        client.convert(pdf_file)
    assert "boom" not in str(excinfo.value)


def test_convert_wraps_transport_errors(pdf_file: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(ConversionError):
        _client(httpx.MockTransport(handler)).convert(pdf_file)


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
