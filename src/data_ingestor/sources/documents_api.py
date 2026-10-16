"""Client for the document store's read-only HTTP API.

The document store (llc-manager) serves metadata and stored files over three routes under
``/api/v1/documents``: a paginated list, one document's metadata, and the file bytes. Every
request carries the shared key in ``X-API-Key``. The metadata is the source of the document-level
fields (entity, category, confidentiality, consent) the Chunk stage copies onto each chunk.

Errors carry the HTTP status or exception class only, never a response body, an API key or
document content.
"""

import hashlib
import logging
import os
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from types import TracebackType
from typing import Any, Self

import httpx
from pydantic import BaseModel, ConfigDict, StrictBool, ValidationError

from data_ingestor.core.config import Settings
from data_ingestor.core.exceptions import ConfigurationError, DocumentNotFoundError, DocumentSourceError

logger = logging.getLogger(__name__)

DOCUMENTS_PATH = "/api/v1/documents"
TAX_RETURNS_CATEGORY = "Tax Returns"
DEFAULT_PAGE_SIZE = 200  # the largest page the API serves
DEFAULT_TIMEOUT = 60.0
# The file is handed to docling-serve next, so the cap matches its upload limit.
DEFAULT_MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024
MAX_PAGES = 10_000
_LIST_ATTEMPTS = 2  # one read and one re-read when the rows do not match the total
_RATE_LIMIT_RETRIES = 4
_RETRY_AFTER_CAP_SECONDS = 60.0
_CONNECT_RETRIES = 2  # connection-establishment retries only
_DOWNLOAD_BLOCK_BYTES = 64 * 1024
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_MIME_EXTENSIONS = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/tiff": ".tiff",
    "text/plain": ".txt",
}
_FALLBACK_EXTENSION = ".bin"


class DocumentRecord(BaseModel):
    """One document's metadata as the documents API serves it (the cross-service contract).

    ``consent_on_file`` and ``is_confidential`` are strict booleans: a string such as ``"true"``
    is rejected, so consent can never be read from a mistyped value. Fields the API adds later
    are ignored. The API never returns a file path.
    """

    model_config = ConfigDict(extra="ignore", frozen=True)

    id: uuid.UUID
    title: str
    category: str
    document_type: str
    entity_id: uuid.UUID
    document_date: date | None = None
    effective_date: date | None = None
    is_confidential: StrictBool
    consent_on_file: StrictBool
    sha256: str | None = None
    mime_type: str | None = None
    file_size: int | None = None
    created_at: datetime
    updated_at: datetime

    def document_fields(self, sha256: str | None = None) -> dict[str, Any]:
        """Return the document-level fields a chunk set carries.

        Args:
            sha256: Hash of the file actually downloaded; defaults to the hash the API reported

        Returns:
            The fields ``build_chunk_set`` and ``reconcile_consent`` read
        """
        return {
            "entity_id": str(self.entity_id),
            "document_type": self.document_type,
            "category": self.category,
            "is_confidential": self.is_confidential,
            "consent_on_file": self.consent_on_file,
            "title": self.title,
            "document_date": self.document_date.isoformat() if self.document_date else None,
            "sha256": sha256 if sha256 is not None else self.sha256,
        }


@dataclass(frozen=True)
class DownloadedFile:
    """A document file written to local disk, with the hash of the bytes written."""

    path: Path
    sha256: str


def _canonical_uuid(value: str | uuid.UUID) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except ValueError as exc:
        msg = "document id must be a UUID"
        raise DocumentSourceError(msg) from exc


def _utc_isoformat(moment: datetime) -> str:
    """Format a time for ``updated_since``; a time without a zone is read as UTC."""
    aware = moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment
    return aware.astimezone(UTC).isoformat()


def _extension(content_type: str | None) -> str:
    mime = (content_type or "").split(";")[0].strip().lower()
    return _MIME_EXTENSIONS.get(mime, _FALLBACK_EXTENSION)


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    """Seconds to wait after a 429: ``Retry-After`` when it is a number, else back off."""
    header = response.headers.get("Retry-After", "")
    try:
        delay = float(header)
    except ValueError:
        delay = float(2**attempt)
    return max(0.0, min(delay, _RETRY_AFTER_CAP_SECONDS))


def _status_error(status: int) -> DocumentSourceError:
    if status == httpx.codes.UNAUTHORIZED:
        return DocumentSourceError("documents API rejected the API key (HTTP 401)")
    if status == httpx.codes.SERVICE_UNAVAILABLE:
        return DocumentSourceError("documents API has no API key configured on the server (HTTP 503; not configured)")
    return DocumentSourceError(f"documents API returned HTTP {status}")


def _resolve_api_key(settings: Settings) -> str:
    """Return the API key from the key setting or the key file; exactly one must be set."""
    inline = settings.llc_manager_api_key
    key_file = settings.llc_manager_api_key_file
    if inline is not None and key_file is not None:
        msg = "set either LLC_MANAGER_API_KEY or LLC_MANAGER_API_KEY_FILE, not both"
        raise ConfigurationError(msg)
    if inline is not None:
        key = inline.get_secret_value().strip()
    elif key_file is not None:
        try:
            key = key_file.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError) as exc:
            msg = f"cannot read the API key file: {type(exc).__name__}"
            raise ConfigurationError(msg) from exc
        if "\n" in key or "\r" in key:
            msg = "the API key file must hold the key on a single line"
            raise ConfigurationError(msg)
        if not key:
            msg = "the API key file is empty"
            raise ConfigurationError(msg)
    else:
        msg = (
            "no API key is configured; set DATA_INGESTOR_LLC_MANAGER_API_KEY or DATA_INGESTOR_LLC_MANAGER_API_KEY_FILE"
        )
        raise ConfigurationError(msg)
    if not key:
        msg = "the configured API key is empty"
        raise ConfigurationError(msg)
    return key


class DocumentsApiClient:
    """Reads documents from the document store's HTTP API."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = DEFAULT_TIMEOUT,
        transport: httpx.BaseTransport | None = None,
        max_download_bytes: int = DEFAULT_MAX_DOWNLOAD_BYTES,
        page_size: int = DEFAULT_PAGE_SIZE,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """Initialize the client.

        Args:
            base_url: Document store base URL (http or https), taken from configuration
            api_key: Key sent as ``X-API-Key``
            timeout: Request timeout in seconds
            transport: Optional transport override, used by tests
            max_download_bytes: Largest file this client will download
            page_size: Items requested per list page
            sleep: Sleep function used while rate limited, replaceable in tests

        Raises:
            ConfigurationError: If ``base_url`` is not an http(s) URL with a host, or is plain http
                to a host that is not loopback
        """
        try:
            url = httpx.URL(base_url)
        except httpx.InvalidURL as exc:
            msg = "the documents API base URL is not a valid URL"
            raise ConfigurationError(msg) from exc
        if url.scheme not in {"http", "https"} or not url.host:
            msg = "the documents API base URL must be an http or https URL with a host"
            raise ConfigurationError(msg)
        if url.scheme == "http" and url.host not in _LOOPBACK_HOSTS:
            # #CRITICAL: Security: the key and the documents must not cross a network in clear text
            # #VERIFY: tests/unit/test_documents_api_client.py::test_plain_http_to_a_remote_host_is_refused
            msg = "the documents API base URL must use https unless the host is loopback"
            raise ConfigurationError(msg)

        self._max_download_bytes = max_download_bytes
        self._page_size = page_size
        self._sleep = sleep
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"X-API-Key": api_key},
            timeout=timeout,
            transport=transport or httpx.HTTPTransport(retries=_CONNECT_RETRIES),
        )

    @classmethod
    def from_settings(cls, settings: Settings, transport: httpx.BaseTransport | None = None) -> Self:
        """Build a client from application settings.

        Raises:
            ConfigurationError: If the URL is unset or invalid, or the key is missing, empty,
                unreadable, or given both directly and as a file
        """
        if not settings.llc_manager_url:
            msg = "DATA_INGESTOR_LLC_MANAGER_URL is not set"
            raise ConfigurationError(msg)
        return cls(
            settings.llc_manager_url,
            _resolve_api_key(settings),
            timeout=settings.llc_manager_timeout,
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

    # -- requests ----------------------------------------------------------------

    def _request(self, path: str, params: dict[str, Any] | None, *, stream: bool) -> httpx.Response:
        try:
            request = self._client.build_request("GET", path, params=params)
            return self._client.send(request, stream=stream)
        except httpx.HTTPError as exc:
            msg = f"documents API request failed: {type(exc).__name__}"
            raise DocumentSourceError(msg) from exc

    def _send(self, path: str, params: dict[str, Any] | None = None, *, stream: bool = False) -> httpx.Response:
        """Send a GET, waiting and retrying while the API rate limits the caller (HTTP 429)."""
        # #EDGE: Rate limit: the API allows about 60 requests a minute per client address
        # #VERIFY: tests/unit/test_documents_api_client.py::test_a_rate_limited_request_waits_for_retry_after_and_retries
        attempt = 0
        while True:
            response = self._request(path, params, stream=stream)
            if response.status_code != httpx.codes.TOO_MANY_REQUESTS or attempt >= _RATE_LIMIT_RETRIES:
                return response
            delay = _retry_delay(response, attempt)
            response.close()
            logger.info("Documents API rate limited the request; waiting %.0f seconds", delay)
            self._sleep(delay)
            attempt += 1

    @staticmethod
    def _json(response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError as exc:
            msg = "documents API returned a body that is not JSON"
            raise DocumentSourceError(msg) from exc

    @staticmethod
    def _record(raw: object) -> DocumentRecord:
        try:
            return DocumentRecord.model_validate(raw)
        except ValidationError:
            # The validation error would repeat field values, so it is not chained or shown.
            msg = "documents API returned a document record that failed validation"
            raise DocumentSourceError(msg) from None

    # -- reading documents ---------------------------------------------------------

    def list_documents(
        self,
        *,
        updated_since: datetime | None = None,
        category: str | None = None,
    ) -> list[DocumentRecord]:
        """List documents, oldest ``updated_at`` first, following every page.

        Paging is by offset and an edit while paging can repeat a row, so the result is
        de-duplicated by ID, keeping the newest copy. Soft-deleted documents are not listed.

        Args:
            updated_since: Only documents updated at or after this time (no zone means UTC). The
                service stamps ``updated_at`` with the time its transaction started, so a row can
                commit after a later one has been listed. A caller that re-polls with the newest
                ``updated_at`` it saw must subtract a margin (at least five minutes) first.
            category: Only documents in this category

        Returns:
            The records, ordered by ``updated_at`` then ID

        Raises:
            DocumentSourceError: On a transport failure, an HTTP error status, or a body that
                is not a page of valid records
        """
        params: dict[str, Any] = {"size": self._page_size}
        if updated_since is not None:
            params["updated_since"] = _utc_isoformat(updated_since)
        if category is not None:
            params["category"] = category

        # #CRITICAL: Data Integrity: offset paging ordered by updated_at can skip a row when a
        # document is edited while the pages are read, and a skipped tax return would miss its
        # consent check. Every page's total is compared with page 1's and with the rows read, and
        # a mismatch is read again once, then fails the run.
        # #VERIFY: tests/unit/test_documents_api_client.py::test_a_skipped_row_is_listed_again_and_the_second_listing_is_used
        for _attempt in range(_LIST_ATTEMPTS):
            records = self._read_pages(params)
            if records is not None:
                return sorted(records.values(), key=lambda r: (r.updated_at, str(r.id)))
            logger.warning("Document listing did not match its reported total; listing again")
        msg = "documents API listing did not match its reported total after a second read"
        raise DocumentSourceError(msg)

    def _read_pages(self, params: dict[str, Any]) -> dict[uuid.UUID, DocumentRecord] | None:
        """Read every page once; return None when the listing moved while it was being read.

        Every page must report the same total as page 1, and the distinct rows read must equal it.
        A changed total proves a row was created or removed mid-read; the row count alone cannot,
        because an edit that skips one row and a create that adds another cancel out.
        """
        records: dict[uuid.UUID, DocumentRecord] = {}
        page = 1
        total = 0
        while True:
            items, pages, page_total = self._fetch_page(params, page)
            if page == 1:
                total = page_total
            elif page_total != total:
                return None
            self._merge(records, items)
            if page >= pages:
                break
            if not items:
                return None  # an empty page before the last one means rows moved
            page += 1
        return records if len(records) == total else None

    def _fetch_page(self, params: dict[str, Any], page: int) -> tuple[list[object], int, int]:
        response = self._send(DOCUMENTS_PATH, {**params, "page": page})
        if response.status_code != httpx.codes.OK:
            raise _status_error(response.status_code)
        return self._parse_page(self._json(response))

    def _merge(self, records: dict[uuid.UUID, DocumentRecord], items: list[object]) -> None:
        """Add the page's records, keeping the newest copy of one that repeats."""
        for raw in items:
            record = self._record(raw)
            known = records.get(record.id)
            if known is None or record.updated_at >= known.updated_at:
                records[record.id] = record

    @staticmethod
    def _parse_page(body: object) -> tuple[list[object], int, int]:
        items = body.get("items") if isinstance(body, dict) else None
        pages = body.get("pages") if isinstance(body, dict) else None
        total = body.get("total") if isinstance(body, dict) else None
        if (
            not isinstance(items, list)
            or not isinstance(pages, int)
            or isinstance(pages, bool)
            or pages < 1
            or not isinstance(total, int)
            or isinstance(total, bool)
            or total < 0
        ):
            msg = "documents API returned an unexpected page shape"
            raise DocumentSourceError(msg)
        if pages > MAX_PAGES:
            msg = f"documents API reported {pages} pages, more than the {MAX_PAGES} page limit"
            raise DocumentSourceError(msg)
        return items, pages, total

    def get_document(self, document_id: str | uuid.UUID) -> DocumentRecord | None:
        """Fetch one document's current metadata.

        Returns:
            The record, or None when the document does not exist or has been deleted

        Raises:
            DocumentSourceError: On a transport failure, an HTTP error status, or an invalid record
        """
        response = self._send(f"{DOCUMENTS_PATH}/{_canonical_uuid(document_id)}")
        if response.status_code == httpx.codes.NOT_FOUND:
            return None
        if response.status_code != httpx.codes.OK:
            raise _status_error(response.status_code)
        return self._record(self._json(response))

    def download_file(self, document_id: str | uuid.UUID, directory: Path) -> DownloadedFile:
        """Stream a document's file into ``directory`` and hash it as it is written.

        The file is named ``{document_id}`` plus an extension chosen from the response type and
        created with mode 0600. A failed or oversized download leaves no partial file.

        Raises:
            DocumentNotFoundError: If the document or its file does not exist (HTTP 404)
            DocumentSourceError: On a transport failure, any other error status, or a file over
                the size limit
        """
        document_text = _canonical_uuid(document_id)
        response = self._send(f"{DOCUMENTS_PATH}/{document_text}/file", stream=True)
        try:
            if response.status_code == httpx.codes.NOT_FOUND:
                msg = "documents API has no file for the document (HTTP 404)"
                raise DocumentNotFoundError(msg)
            if response.status_code != httpx.codes.OK:
                raise _status_error(response.status_code)
            self._check_declared_size(response)
            target = directory / f"{document_text}{_extension(response.headers.get('Content-Type'))}"
            return DownloadedFile(target, self._write_stream(response, target))
        finally:
            response.close()

    def _check_declared_size(self, response: httpx.Response) -> None:
        declared = response.headers.get("Content-Length", "")
        if declared.isdigit() and int(declared) > self._max_download_bytes:
            msg = f"document file is larger than the {self._max_download_bytes} byte limit"
            raise DocumentSourceError(msg)

    def _write_stream(self, response: httpx.Response, target: Path) -> str:
        digest = hashlib.sha256()
        written = 0
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "wb") as handle:
                for block in response.iter_bytes(_DOWNLOAD_BLOCK_BYTES):
                    written += len(block)
                    if written > self._max_download_bytes:
                        msg = f"document file is larger than the {self._max_download_bytes} byte limit"
                        raise DocumentSourceError(msg)
                    digest.update(block)
                    handle.write(block)
        except httpx.HTTPError as exc:
            target.unlink(missing_ok=True)
            msg = f"documents API download failed: {type(exc).__name__}"
            raise DocumentSourceError(msg) from exc
        except BaseException:
            target.unlink(missing_ok=True)
            raise
        return digest.hexdigest()
