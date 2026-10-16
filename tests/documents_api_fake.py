"""An in-process fake of the document store's read-only HTTP API.

It speaks the documents API shape (``GET /api/v1/documents``, ``/{id}`` and
``/{id}/file``, authenticated with ``X-API-Key``) over ``httpx.MockTransport``,
so tests exercise the real client, JSON parsing and paging with no network.
Everything here is synthetic.
"""

import hashlib
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx

API_KEY = "test-key-0123456789-0123456789-0123456789"
BASE_URL = "https://documents.example.test"
DOCUMENTS_PATH = "/api/v1/documents"
PDF_BYTES = b"%PDF-1.4 synthetic"


def _ts(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def make_document(
    *,
    document_id: str | None = None,
    title: str = "Synthetic Operating Agreement",
    category: str = "LLCs",
    document_type: str = "operating_agreement",
    entity_id: str = "11111111-1111-4111-8111-111111111111",
    consent_on_file: bool = False,
    is_confidential: bool = True,
    updated_at: datetime | None = None,
    content: bytes = PDF_BYTES,
    sha256: str | None = "auto",
    mime_type: str = "application/pdf",
) -> dict[str, Any]:
    """A ``DocumentRead`` record plus its file bytes under the ``_content`` key."""
    stamp = updated_at or datetime(2026, 1, 1, tzinfo=UTC)
    return {
        "id": document_id or str(uuid.uuid4()),
        "title": title,
        "category": category,
        "document_type": document_type,
        "entity_id": entity_id,
        "document_date": "2025-06-30",
        "effective_date": None,
        "is_confidential": is_confidential,
        "consent_on_file": consent_on_file,
        "sha256": hashlib.sha256(content).hexdigest() if sha256 == "auto" else sha256,
        "mime_type": mime_type,
        "file_size": len(content),
        "created_at": _ts(stamp),
        "updated_at": _ts(stamp),
        "_content": content,
    }


def make_tax_return(*, consent_on_file: bool, **kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault("title", "Synthetic Tax Return")
    return make_document(
        category="Tax Returns",
        document_type="tax_return",
        consent_on_file=consent_on_file,
        **kwargs,
    )


class FakeDocumentsApi:
    """State and request log of the fake service."""

    def __init__(self, documents: list[dict[str, Any]] | None = None, *, api_key: str = API_KEY) -> None:
        self.documents: dict[str, dict[str, Any]] = {}
        self.api_key = api_key
        self.requests: list[tuple[str, dict[str, str]]] = []
        # Hooks and fault injection used by individual tests.
        self.before_detail: Callable[[str], None] | None = None
        self.rate_limit_first: int = 0
        self.file_status: dict[str, int] = {}
        self.detail_status: dict[str, int] = {}
        self.max_page_size = 200
        for document in documents or []:
            self.add(document)

    def add(self, document: dict[str, Any]) -> dict[str, Any]:
        self.documents[document["id"]] = document
        return document

    def set_consent(self, document_id: str, value: bool) -> None:
        self.documents[document_id]["consent_on_file"] = value

    def delete(self, document_id: str) -> None:
        """Soft-delete: the document leaves the list and its detail and file return 404."""
        self.documents.pop(document_id, None)

    @property
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._handle)

    def paths(self) -> list[str]:
        return [path for path, _query in self.requests]

    def file_requests(self) -> list[str]:
        return [path for path in self.paths() if path.endswith("/file")]

    # -- request handling ----------------------------------------------------

    def _handle(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        query = dict(request.url.params)
        self.requests.append((path, query))
        return self._refuse(request) or self._route(path, query)

    def _refuse(self, request: httpx.Request) -> httpx.Response | None:
        """A rate-limit or key rejection, or None when the request goes through."""
        if self.rate_limit_first > 0:
            self.rate_limit_first -= 1
            return httpx.Response(429, headers={"Retry-After": "1"}, json={"detail": "rate limited"})
        if request.headers.get("X-API-Key") != self.api_key:
            return httpx.Response(401, json={"detail": "Invalid API key: secret-detail"})
        return None

    def _route(self, path: str, query: dict[str, str]) -> httpx.Response:
        if path == DOCUMENTS_PATH:
            return self._list(query)
        if not path.startswith(f"{DOCUMENTS_PATH}/"):
            return httpx.Response(404, json={"detail": "Not Found"})
        document_id, _, tail = path[len(DOCUMENTS_PATH) + 1 :].partition("/")
        return self._file(document_id) if tail == "file" else self._detail(document_id)

    @staticmethod
    def _public(document: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in document.items() if not key.startswith("_")}

    def _list(self, query: dict[str, str]) -> httpx.Response:
        items = sorted(self.documents.values(), key=lambda d: (d["updated_at"], d["id"]))
        if "updated_since" in query:
            since = datetime.fromisoformat(query["updated_since"])
            if since.tzinfo is None:
                since = since.replace(tzinfo=UTC)
            items = [d for d in items if datetime.fromisoformat(d["updated_at"]) >= since]
        if "category" in query:
            items = [d for d in items if d["category"] == query["category"]]
        size = min(int(query.get("size", "50")), self.max_page_size)
        page = int(query.get("page", "1"))
        total = len(items)
        window = items[(page - 1) * size : page * size]
        body = {
            "items": [self._public(d) for d in window],
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size if total else 1,
        }
        return httpx.Response(200, json=body)

    def _detail(self, document_id: str) -> httpx.Response:
        if self.before_detail is not None:
            self.before_detail(document_id)
        if document_id in self.detail_status:
            return httpx.Response(self.detail_status[document_id], json={"detail": "secret-detail"})
        document = self.documents.get(document_id)
        if document is None:
            return httpx.Response(404, json={"detail": "Document not found"})
        return httpx.Response(200, json=self._public(document))

    def _file(self, document_id: str) -> httpx.Response:
        document = self.documents.get(document_id)
        if document is None or self.file_status.get(document_id, 200) == 404:
            return httpx.Response(404, json={"detail": "Document file not found"})
        content: bytes = document["_content"]
        return httpx.Response(
            200,
            content=content,
            headers={"Content-Type": document["mime_type"], "Content-Length": str(len(content))},
        )
