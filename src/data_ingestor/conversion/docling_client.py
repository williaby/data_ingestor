"""Client for the docling-serve conversion API.

The conversion call sits behind the ``DocumentConverter`` protocol so another
service can take it over later without touching callers.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import httpx

from data_ingestor.core.exceptions import ConversionError

logger = logging.getLogger(__name__)

CONVERT_PATH = "/v1/convert/file"
_OK_STATUSES = {"success", "partial_success"}


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
        ...


class DoclingServeClient:
    """Calls docling-serve ``POST /v1/convert/file`` and returns the JSON document."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout: float = 300.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        """Initialize the client.

        Args:
            base_url: docling-serve base URL, taken from configuration
            api_key: Optional key sent as X-Api-Key when the service requires one
            timeout: Request timeout in seconds
            transport: Optional transport override, used by tests
        """
        headers = {"X-Api-Key": api_key} if api_key else {}
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
            transport=transport,
        )

    def close(self) -> None:
        """Release the underlying connection pool."""
        self._client.close()

    def convert(self, path: Path) -> ConversionResult:
        """Convert a file to Docling JSON.

        # #CRITICAL: External Resources: The service may be down or return partial output
        # #VERIFY: Errors never include document text, only status and file name

        Raises:
            ConversionError: On transport failure, non-2xx status, or a missing JSON body
        """
        try:
            with path.open("rb") as handle:
                response = self._client.post(
                    CONVERT_PATH,
                    files={"files": (path.name, handle, "application/octet-stream")},
                    data={"to_formats": "json", "do_ocr": "true", "abort_on_error": "false"},
                )
        except (httpx.HTTPError, OSError) as exc:
            msg = f"docling-serve request failed for {path.name}: {type(exc).__name__}"
            raise ConversionError(msg) from exc

        if response.status_code != httpx.codes.OK:
            msg = f"docling-serve returned HTTP {response.status_code} for {path.name}"
            raise ConversionError(msg)

        try:
            body = response.json()
        except ValueError as exc:
            msg = f"docling-serve returned a non-JSON body for {path.name}"
            raise ConversionError(msg) from exc

        status = str(body.get("status", ""))
        json_content = (body.get("document") or {}).get("json_content")
        if status not in _OK_STATUSES or not isinstance(json_content, dict) or not json_content:
            msg = f"docling-serve conversion of {path.name} did not produce a document (status={status or 'missing'})"
            raise ConversionError(msg)

        if status == "partial_success":
            logger.warning("docling-serve reported partial success for %s", path.name)
        return ConversionResult(docling_json=json_content, status=status, filename=path.name)
