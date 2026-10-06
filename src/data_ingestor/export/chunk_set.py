"""Chunk-set output: the RAGChunkSet.json the Chunk stage hands to applications.

The shape follows ``chunk-embed-contract.md`` (version 1.1) in
image-preprocessing-detector. The stage ends here: it writes files and does not
embed, store vectors, or search. An application reads the directory.

Tax returns are gated on consent. A tax return is chunked only when its
``consent_on_file`` is exactly ``True``. When consent is withdrawn, its chunk
set is replaced by one with ``consent_on_file`` false and no chunks, so the
reading application sees the change and removes what it indexed.
"""

import json
import logging
import os
import tempfile
import uuid
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Any

import tiktoken

from data_ingestor.core.exceptions import ChunkingError
from data_ingestor.core.models import Chunk

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "1.1"
SOURCE_TRACK = "document"
# The contract fixes this tiktoken encoding for token_count, whatever tokenizer sized the chunks.
TIKTOKEN_ENCODING = "cl100k_base"
DEFAULT_CHUNK_STRATEGY = "hybrid"

# Fixed namespace so the same document always produces the same chunk and trace IDs.
_ID_NAMESPACE = uuid.UUID("5d0c4f7e-3a51-4d0e-9a53-6b1b6a0f2c11")

# Document-level fields written on the set and copied onto every chunk.
CARRIED_FIELDS = (
    "entity_id",
    "document_type",
    "category",
    "is_confidential",
    "consent_on_file",
    "title",
    "document_date",
    "sha256",
)

# A document is a tax return when its category or document type says so.
TAX_RETURN_CATEGORY = "Tax Returns"
TAX_RETURN_DOCUMENT_TYPES = frozenset({"tax_return", "tax_election"})


class ConsentAction(StrEnum):
    """What the consent check decided for one document.

    Attributes:
        NOT_REQUIRED: Not a tax return; chunk it as any other document.
        CHUNK: A tax return with consent whose stored chunk set is missing or
            not consented; convert and chunk it now.
        UNCHANGED: A tax return with consent whose stored chunk set is already
            consented; chunk it only if the document itself changed.
        SKIP: A tax return without consent and no stored chunk set; do not
            convert or chunk it.
        WITHDRAWN: A tax return without consent that had a stored chunk set;
            the set now has ``consent_on_file`` false and no chunks.
    """

    NOT_REQUIRED = "not_required"
    CHUNK = "chunk"
    UNCHANGED = "unchanged"
    SKIP = "skip"
    WITHDRAWN = "withdrawn"


def _require_uuid(value: str, name: str) -> str:
    try:
        return str(uuid.UUID(value))
    except ValueError as exc:
        msg = f"{name} must be a UUID"
        raise ChunkingError(msg) from exc


def is_tax_return(document_fields: Mapping[str, Any]) -> bool:
    """Say whether a document is a tax return and so needs consent.

    Args:
        document_fields: Document-level fields (``category``, ``document_type``)

    Returns:
        True when the category is ``Tax Returns`` or the document type is a
        tax-return type, ignoring case and surrounding spaces.
    """
    category = document_fields.get("category")
    if isinstance(category, str) and category.strip().casefold() == TAX_RETURN_CATEGORY.casefold():
        return True
    document_type = document_fields.get("document_type")
    return isinstance(document_type, str) and document_type.strip().casefold() in TAX_RETURN_DOCUMENT_TYPES


def _document_values(document_fields: Mapping[str, Any]) -> dict[str, Any]:
    """Pick the carried fields; consent is ``True`` only when given as exactly ``True``."""
    values = {key: document_fields.get(key) for key in CARRIED_FIELDS}
    # #CRITICAL: Security: consent fails closed; a missing, null or non-boolean value is false
    # #VERIFY: tests/unit/test_chunk_set.py::test_consent_is_true_only_when_exactly_true
    values["consent_on_file"] = document_fields.get("consent_on_file") is True
    return values


def _resolve_trace_id(document_id: str, trace_id: str | None) -> str:
    if trace_id:
        return _require_uuid(trace_id, "trace_id")
    return str(uuid.uuid5(_ID_NAMESPACE, f"trace:{document_id}"))


def _set_header(
    document_id: str,
    trace_id: str,
    chunk_strategy: str,
    values: Mapping[str, Any],
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "document_id": document_id,
        "trace_id": trace_id,
        "source_track": SOURCE_TRACK,
        "chunk_strategy": chunk_strategy,
        "total_chunks": len(entries),
        **values,
        "chunks": entries,
    }


def build_chunk_set(
    document_id: str,
    chunks: list[Chunk],
    chunk_strategy: str,
    *,
    document_fields: Mapping[str, Any],
    trace_id: str | None = None,
) -> dict[str, Any]:
    """Build a RAGChunkSet dictionary from chunks.

    ``trust_score``, ``ocr_engine_provenance`` and ``hallucination_risk`` are
    ``None`` (JSON null): this stage has no scoring yet, and null means "not
    scored", never zero or one.

    The fields in ``CARRIED_FIELDS`` are taken from ``document_fields`` and
    written on the set and on every chunk, so all chunks of a document carry
    the same ``consent_on_file``.

    # #CRITICAL: Citation Integrity: every chunk needs a page range; a chunk without one fails
    # #VERIFY: tests/unit/test_chunk_set.py::test_chunk_without_page_fails
    # #CRITICAL: Security: a tax return without consent on file is never chunked
    # #VERIFY: tests/unit/test_chunk_set.py::test_tax_return_without_consent_is_refused

    Args:
        document_id: Stable document UUID (from the document store)
        chunks: Chunks in document order
        chunk_strategy: Strategy name written on the set and on every chunk
        document_fields: Document-level values from the document store record,
            including ``consent_on_file``
        trace_id: Pipeline trace UUID. When absent, one is derived from the
            document ID so output stays reproducible.

    Returns:
        The chunk set, ready for ``write_chunk_set``

    Raises:
        ChunkingError: If an ID is not a UUID, a chunk has no page range, or
            the document is a tax return without consent on file
    """
    document_id = _require_uuid(document_id, "document_id")
    trace_id = _resolve_trace_id(document_id, trace_id)
    values = _document_values(document_fields)
    if is_tax_return(values) and not values["consent_on_file"]:
        msg = f"Document {document_id} is a tax return without consent on file and must not be chunked"
        raise ChunkingError(msg)
    encoding = tiktoken.get_encoding(TIKTOKEN_ENCODING)

    entries: list[dict[str, Any]] = []
    for index, chunk in enumerate(chunks):
        if chunk.start_page is None or chunk.end_page is None:
            msg = f"Chunk {index} of document {document_id} has no page range"
            raise ChunkingError(msg)
        entry: dict[str, Any] = {
            "chunk_id": str(uuid.uuid5(_ID_NAMESPACE, f"chunk:{document_id}:{index}:{chunk.content}")),
            "document_id": document_id,
            "trace_id": trace_id,
            "text": chunk.content,
            "page_range": [chunk.start_page, chunk.end_page],
            "section_hierarchy": list(chunk.metadata.get("section_hierarchy") or []),
            "trust_score": None,
            "ocr_engine_provenance": None,
            "chunk_strategy": chunk_strategy,
            "token_count": len(encoding.encode(chunk.content, disallowed_special=())),
            "source_track": SOURCE_TRACK,
            "hallucination_risk": None,
        }
        entry.update(values)
        entries.append(entry)

    return _set_header(document_id, trace_id, chunk_strategy, values, entries)


def build_withdrawn_chunk_set(
    document_id: str,
    document_fields: Mapping[str, Any],
    *,
    chunk_strategy: str = DEFAULT_CHUNK_STRATEGY,
    trace_id: str | None = None,
) -> dict[str, Any]:
    """Build the chunk set that replaces a document whose consent was withdrawn.

    It keeps the document-level fields, sets ``consent_on_file`` to false, and
    has no chunks, so no chunk text remains on disk.

    Args:
        document_id: Stable document UUID (from the document store)
        document_fields: Document-level values from the document store record
        chunk_strategy: Strategy name written on the set
        trace_id: Pipeline trace UUID, derived from the document ID when absent

    Returns:
        The chunk set, ready for ``write_chunk_set``

    Raises:
        ChunkingError: If an ID is not a UUID
    """
    document_id = _require_uuid(document_id, "document_id")
    trace_id = _resolve_trace_id(document_id, trace_id)
    values = _document_values(document_fields)
    values["consent_on_file"] = False
    return _set_header(document_id, trace_id, chunk_strategy, values, [])


def _chunk_set_path(output_dir: Path, document_id: str) -> Path:
    return output_dir / f"{document_id}.json"


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def stored_consent(output_dir: Path, document_id: str) -> bool | None:
    """Read the consent recorded in a document's existing chunk set.

    Consent counts as given only when every ``consent_on_file`` value in the
    file (on the set and on each chunk) is exactly ``True``; a missing value
    is false. A file that cannot be read or parsed counts as not consented.

    Args:
        output_dir: Chunk-set directory
        document_id: Document UUID

    Returns:
        None when the document has no chunk set, otherwise the stored consent

    Raises:
        ChunkingError: If the document ID is not a UUID
    """
    document_id = _require_uuid(document_id, "document_id")
    path = _chunk_set_path(output_dir, document_id)
    if not path.exists():
        return None
    try:
        raw = _read_json(path)
    except (OSError, UnicodeDecodeError, ValueError):
        return False
    if not isinstance(raw, dict):
        return False
    seen: list[object] = []
    if "consent_on_file" in raw:
        seen.append(raw["consent_on_file"])
    chunks = raw.get("chunks")
    if isinstance(chunks, list):
        seen.extend(item.get("consent_on_file", False) if isinstance(item, dict) else False for item in chunks)
    return bool(seen) and all(value is True for value in seen)


def reconcile_consent(
    document_id: str,
    document_fields: Mapping[str, Any],
    output_dir: Path,
) -> ConsentAction:
    """Apply the tax-return consent rules to one document before chunking it.

    Consent can change without the document's hash or update time changing,
    so callers run this for every tax return on every run, comparing the
    document store value with the stored chunk set:

    * consent given: ``CHUNK`` when the stored set is missing or not
      consented, otherwise ``UNCHANGED``;
    * consent not given and a stored set exists: the set is replaced with
      ``build_withdrawn_chunk_set`` (``WITHDRAWN``);
    * consent not given and no stored set: ``SKIP``, nothing is written.

    Skips and withdrawals are logged by document ID only.

    # #EDGE: Consent is withdrawn after the document was chunked and indexed
    # #VERIFY: tests/unit/test_chunk_set.py::test_withdrawn_consent_rewrites_the_chunk_set

    Args:
        document_id: Document UUID
        document_fields: Document-level values from the document store record
        output_dir: Chunk-set directory

    Returns:
        What the caller should do next

    Raises:
        ChunkingError: If the document ID is not a UUID
    """
    document_id = _require_uuid(document_id, "document_id")
    if not is_tax_return(document_fields):
        return ConsentAction.NOT_REQUIRED
    stored = stored_consent(output_dir, document_id)
    if document_fields.get("consent_on_file") is True:
        return ConsentAction.UNCHANGED if stored is True else ConsentAction.CHUNK
    if stored is None:
        logger.info("Skipped tax return without consent on file: %s", document_id)
        return ConsentAction.SKIP

    withdrawn = build_withdrawn_chunk_set(document_id, document_fields)
    try:
        current: object = _read_json(_chunk_set_path(output_dir, document_id))
    except (OSError, UnicodeDecodeError, ValueError):
        current = None
    if current != withdrawn:
        write_chunk_set(withdrawn, output_dir)
        logger.info("Replaced chunk set after consent withdrawal: %s", document_id)
    return ConsentAction.WITHDRAWN


def write_chunk_set(chunk_set: dict[str, Any], output_dir: Path) -> Path:
    """Write ``{document_id}.json`` into ``output_dir`` atomically.

    The file is written under a temporary name in the same directory, then
    renamed, so a reader never sees a partial file. Writing the same document
    again replaces its file.

    # #CRITICAL: Concurrency: the consuming application polls this directory while we write
    # #VERIFY: Path.replace is atomic on one filesystem; the temp file lives in the target directory

    Args:
        chunk_set: A set from ``build_chunk_set`` or ``build_withdrawn_chunk_set``
        output_dir: Chunk-set directory, created when missing

    Returns:
        Path of the written file

    Raises:
        ChunkingError: If the set has no document ID
    """
    document_id = chunk_set.get("document_id")
    if not document_id:
        msg = "Chunk set has no document_id"
        raise ChunkingError(msg)

    output_dir.mkdir(parents=True, exist_ok=True)
    target = _chunk_set_path(output_dir, document_id)
    payload = json.dumps(chunk_set, indent=2, ensure_ascii=False) + "\n"

    fd, tmp_name = tempfile.mkstemp(dir=output_dir, prefix=f".{document_id}.", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
        tmp_path.chmod(0o644)
        tmp_path.replace(target)  # atomic on one filesystem
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
    return target
