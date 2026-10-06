"""Client for the docling-serve conversion API.

The conversion call sits behind the ``DocumentConverter`` protocol so another
service can take it over later without touching callers.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any, BinaryIO, Protocol, Self

import httpx

from data_ingestor.core.config import Settings
from data_ingestor.core.exceptions import ConversionError

logger = logging.getLogger(__name__)

CONVERT_PATH = "/v1/convert/file"
DEFAULT_MAX_UPLOAD_BYTES = 100 * 1024 * 1024
_OK_STATUSES = frozenset({"success", "partial_success"})
_MAX_STATUS_CHARS = 32
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_CONNECT_RETRIES = 2  # connection-establishment retries only; a request that was sent is never repeated
_FORM_FIELDS = {
    "to_formats": "json",
    "do_ocr": "true",
    "abort_on_error": "false",
    "image_export_mode": "placeholder",  # keep embedded page images out of the JSON tree
}


@dataclass(frozen=True)
class ConversionResult:
    """Structured output of a conversion: the Docling JSON tree plus service status."""

    docling_json: dict[str, Any]
    status: str
    filename: str


class DocumentConverter(Protocol):
    """Anything that can turn a file into a Docling JSON document."""

    def convert(self, path: Path) -> ConversionResult:
        """Convert the file at ``path``."""

    def close(self) -> None:
        """Release any resources held by the converter."""


def _safe_status(value: object) -> str:
    """Return a remote status value that is safe to echo in an error message."""
    if not isinstance(value, str) or not value:
        return "missing"
    return re.sub(r"[^A-Za-z0-9_]", "?", value)[:_MAX_STATUS_CHARS]


class DoclingServeClient:
    """Calls docling-serve ``POST /v1/convert/file`` and returns the JSON document."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout: float = 300.0,
        transport: httpx.BaseTransport | None = None,
        max_upload_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
    ) -> None:
        """Initialize the client.

        Args:
            base_url: docling-serve base URL (http or https), taken from configuration
            api_key: Optional key sent as X-Api-Key when the service requires one
            timeout: Request timeout in seconds
            transport: Optional transport override, used by tests
            max_upload_bytes: Largest file this client will upload

        Raises:
            ValueError: If ``base_url`` is not an http(s) URL with a host
        """
        try:
            url = httpx.URL(base_url)
        except httpx.InvalidURL as exc:
            msg = "docling-serve base URL is not a valid URL"
            raise ValueError(msg) from exc
        if url.scheme not in {"http", "https"} or not url.host:
            msg = "docling-serve base URL must be an http or https URL with a host"
            raise ValueError(msg)
        if api_key and url.scheme == "http" and url.host not in _LOOPBACK_HOSTS:
            logger.warning("docling-serve API key and documents are sent over plain http; use https")

        self._max_upload_bytes = max_upload_bytes
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"X-Api-Key": api_key} if api_key else {},
            timeout=timeout,
            transport=transport or httpx.HTTPTransport(retries=_CONNECT_RETRIES),
        )

    @classmethod
    def from_settings(cls, settings: Settings, transport: httpx.BaseTransport | None = None) -> Self:
        """Build a client from application settings, unwrapping the secret API key."""
        key = settings.docling_serve_api_key
        return cls(
            base_url=settings.docling_serve_url,
            api_key=key.get_secret_value() if key else None,
            timeout=settings.docling_serve_timeout,
            transport=transport,
        )

    def __enter__(self) -> Self:
        """Enter the context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the client on exit."""
        self.close()

    def close(self) -> None:
        """Release the underlying connection pool."""
        self._client.close()

    # #CRITICAL: External Resources: The service may be down or return partial output
    # #VERIFY: tests/unit/test_docling_conversion.py (error-path cases assert no response text
    # appears in the raised message; partial and non-JSON bodies are covered)
    def convert(self, path: Path) -> ConversionResult:
        """Convert a file to Docling JSON.

        Errors never include document text, only the file name, HTTP status or a short
        sanitised service status.

        Raises:
            ConversionError: If the file cannot be read or is over the upload limit, on
                transport failure, any HTTP status other than 200, or a missing or
                malformed JSON body
        """
        try:
            size = path.stat().st_size
            handle = path.open("rb")
        except OSError as exc:
            msg = f"cannot read {path.name} for conversion: {type(exc).__name__}"
            raise ConversionError(msg) from exc
        with handle:
            if size > self._max_upload_bytes:
                msg = f"{path.name} is larger than the {self._max_upload_bytes} byte upload limit"
                raise ConversionError(msg)
            response = self._post(path.name, handle)
        return self._parse(response, path.name)

    def _post(self, filename: str, handle: BinaryIO) -> httpx.Response:
        try:
            return self._client.post(
                CONVERT_PATH,
                files={"files": (filename, handle, "application/octet-stream")},
                data=_FORM_FIELDS,
            )
        except (httpx.HTTPError, OSError) as exc:
            msg = f"docling-serve request failed for {filename}: {type(exc).__name__}"
            raise ConversionError(msg) from exc

    @staticmethod
    def _parse(response: httpx.Response, filename: str) -> ConversionResult:
        if response.status_code != httpx.codes.OK:
            msg = f"docling-serve returned HTTP {response.status_code} for {filename}"
            raise ConversionError(msg)

        try:
            body = response.json()
        except ValueError as exc:
            msg = f"docling-serve returned a non-JSON body for {filename}"
            raise ConversionError(msg) from exc
        if not isinstance(body, dict):
            msg = f"docling-serve returned an unexpected JSON shape for {filename}"
            raise ConversionError(msg)

        status = _safe_status(body.get("status"))
        document = body.get("document")
        json_content = document.get("json_content") if isinstance(document, dict) else None
        if status not in _OK_STATUSES or not isinstance(json_content, dict) or not json_content:
            msg = f"docling-serve conversion of {filename} did not produce a document (status={status})"
            raise ConversionError(msg)

        if status == "partial_success":
            logger.warning("docling-serve reported partial success for %s", filename)
        return ConversionResult(docling_json=json_content, status=status, filename=filename)
