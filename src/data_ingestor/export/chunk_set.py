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

# Mode of a written chunk-set file. #ASSUME: the consuming application reads the directory as a
# different user (for example from another container), so the file is world-readable and access is
# controlled by the permissions on the directory. #VERIFY: confirm the reader's uid and, where the
# directory is shared, restrict it (for example mode 0750 with a shared group) or lower the file mode
# with ``chunks_file_mode``.
DEFAULT_FILE_MODE = 0o644

# A document is a tax return when its category or document type says so. Labels are compared
# case-insensitively with "-" and "_" read as spaces. #ASSUME: these are the labels the document
# store uses. #VERIFY: confirm the label vocabulary with the document store owner; a label outside
# this list is not detected, so the gate is a guard for correctly labelled documents and not a
# classifier.
TAX_RETURN_CATEGORIES = frozenset({"tax return", "tax returns"})
TAX_RETURN_DOCUMENT_TYPES = frozenset({"tax return", "tax election"})


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


def _require_uuid(value: object, name: str) -> str:
    if isinstance(value, str):
        try:
            return str(uuid.UUID(value))
        except ValueError:
            pass
    msg = f"{name} must be a UUID"
    raise ChunkingError(msg)


def _normalise_label(value: object) -> str:
    """Lower-case a label, read ``-`` and ``_`` as spaces and collapse whitespace."""
    if not isinstance(value, str):
        return ""
    return " ".join(value.replace("_", " ").replace("-", " ").casefold().split())


def is_tax_return(document_fields: Mapping[str, Any]) -> bool:
    """Say whether a document is a tax return and so needs consent.

    Args:
        document_fields: Document-level fields (``category``, ``document_type``)

    Returns:
        True when the category is ``Tax Returns`` or the document type is a
        tax-return type, ignoring case, surrounding spaces and ``-`` versus
        ``_`` versus space. A label outside the known vocabulary is not detected.
    """
    if _normalise_label(document_fields.get("category")) in TAX_RETURN_CATEGORIES:
        return True
    return _normalise_label(document_fields.get("document_type")) in TAX_RETURN_DOCUMENT_TYPES


def _require_text_field(document_fields: Mapping[str, Any], key: str) -> None:
    value = document_fields.get(key)
    if not isinstance(value, str) or not value.strip():
        msg = f"Document field {key} must be a non-empty string"
        raise ChunkingError(msg)


def _document_values(document_fields: Mapping[str, Any], *, strict: bool = True) -> dict[str, Any]:
    """Pick the carried fields; consent is ``True`` only when given as exactly ``True``.

    In strict mode (a set that carries chunk text) ``entity_id`` and ``sha256``
    must be non-empty strings and ``is_confidential`` a boolean, so a missing
    value is an error and never a silent null. The withdrawn set carries no text
    and must still be written when the record is incomplete, so it is lenient:
    ``is_confidential`` is then true unless it is exactly ``False``.

    Raises:
        ChunkingError: In strict mode, if a required field is missing or mistyped
    """
    values = {key: document_fields.get(key) for key in CARRIED_FIELDS}
    if strict:
        # #CRITICAL: Security: a chunk never goes out without its entity, hash and confidentiality flag
        # #VERIFY: tests/unit/test_chunk_set.py::test_missing_document_fields_are_an_error
        _require_text_field(document_fields, "entity_id")
        _require_text_field(document_fields, "sha256")
        if not isinstance(values["is_confidential"], bool):
            msg = "Document field is_confidential must be a boolean"
            raise ChunkingError(msg)
    else:
        values["is_confidential"] = values["is_confidential"] is not False
    # #CRITICAL: Security: consent fails closed; a missing, null or non-boolean value is false
    # #VERIFY: tests/unit/test_chunk_set.py::test_consent_is_true_only_when_exactly_true
    values["consent_on_file"] = document_fields.get("consent_on_file") is True
    return values


def _load_encoding() -> tiktoken.Encoding:
    """Load the contract's tiktoken encoding, turning a failed load into ``ChunkingError``."""
    # #ASSUME: tiktoken can fetch cl100k_base on first use (it downloads the vocabulary), so an
    # offline host needs the file in TIKTOKEN_CACHE_DIR beforehand
    # #VERIFY: tests/unit/test_chunk_set.py::test_unavailable_encoding_is_a_chunking_error
    try:
        return tiktoken.get_encoding(TIKTOKEN_ENCODING)
    except (OSError, ValueError, RuntimeError) as exc:
        msg = f"tiktoken encoding {TIKTOKEN_ENCODING} is unavailable; set TIKTOKEN_CACHE_DIR on an offline host"
        raise ChunkingError(msg) from exc


def _require_page_range(chunk: Chunk, index: int, document_id: str) -> tuple[int, int]:
    start, end = chunk.start_page, chunk.end_page
    if start is None or end is None:
        msg = f"Chunk {index} of document {document_id} has no page range"
        raise ChunkingError(msg)
    if start < 1 or end < start:
        msg = f"Chunk {index} of document {document_id} has an invalid page range"
        raise ChunkingError(msg)
    return start, end


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
    # #CRITICAL: Security: a document labelled as a tax return without consent on file is never chunked
    # #VERIFY: tests/unit/test_chunk_set.py::test_tax_return_without_consent_is_refused (a label outside
    # the known vocabulary is not detected; see TAX_RETURN_CATEGORIES)

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
        ChunkingError: If an ID is not a UUID, ``entity_id`` or ``sha256`` is
            missing or empty, ``is_confidential`` is not a boolean, a chunk has
            no valid page range, the document is a tax return without consent
            on file, or the tiktoken encoding cannot be loaded
    """
    document_id = _require_uuid(document_id, "document_id")
    trace_id = _resolve_trace_id(document_id, trace_id)
    values = _document_values(document_fields)
    if is_tax_return(values) and not values["consent_on_file"]:
        msg = f"Document {document_id} is a tax return without consent on file and must not be chunked"
        raise ChunkingError(msg)
    encoding = _load_encoding()

    entries: list[dict[str, Any]] = []
    for index, chunk in enumerate(chunks):
        start_page, end_page = _require_page_range(chunk, index, document_id)
        entry: dict[str, Any] = {
            "chunk_id": str(uuid.uuid5(_ID_NAMESPACE, f"chunk:{document_id}:{index}:{chunk.content}")),
            "document_id": document_id,
            "trace_id": trace_id,
            "text": chunk.content,
            "page_range": [start_page, end_page],
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
    has no chunks, so no chunk text remains on disk. It does not require the
    record to be complete: a missing field stays null and ``is_confidential``
    becomes true unless it is exactly false, because failing to write the
    withdrawal would leave consented text on disk.

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
    # Lenient on purpose: a withdrawal must be written even when the record is incomplete.
    values = _document_values(document_fields, strict=False)
    values["consent_on_file"] = False
    return _set_header(document_id, trace_id, chunk_strategy, values, [])


def _chunk_set_path(output_dir: Path, document_id: str) -> Path:
    return output_dir / f"{document_id}.json"


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def stored_consent(output_dir: Path, document_id: str) -> bool | None:
    """Read the consent recorded in a document's existing chunk set.

    Consent counts as given only when the set's ``consent_on_file`` and the
    value on each chunk are all exactly ``True``; a missing value, a missing
    set-level key or a ``chunks`` value that is not a list is false. A file
    that cannot be read or parsed counts as not consented.

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
    except (OSError, ValueError, RecursionError):
        return False
    if not isinstance(raw, dict):
        return False
    chunks = raw.get("chunks")
    if raw.get("consent_on_file") is not True or not isinstance(chunks, list):
        return False
    return all(isinstance(item, dict) and item.get("consent_on_file") is True for item in chunks)


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
    # #ASSUME: one process at a time reconciles and writes a given document; the read of the
    # stored set and the write that follows are not atomic together
    # #VERIFY: run the consent sweep from a single scheduled job per chunk directory

    Args:
        document_id: Document UUID
        document_fields: Document-level values from the document store record
        output_dir: Chunk-set directory

    Returns:
        What the caller should do next

    Raises:
        ChunkingError: If the document ID is not a UUID
        OSError: If the withdrawal write fails. The stored set, which may still
            hold consented chunk text, is then unchanged, so the caller must
            treat this as a failed withdrawal and retry it.
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
    except (OSError, ValueError, RecursionError):
        current = None
    if current != withdrawn:
        write_chunk_set(withdrawn, output_dir)
        logger.info("Replaced chunk set after consent withdrawal: %s", document_id)
    return ConsentAction.WITHDRAWN


def _fsync_directory(directory: Path) -> None:
    """Flush a directory entry to disk where the platform allows it."""
    try:
        fd = os.open(directory, os.O_RDONLY)
    except OSError:
        return  # some platforms cannot open a directory
    try:
        os.fsync(fd)
    except OSError:
        logger.debug("Directory fsync is not supported here")
    finally:
        os.close(fd)


def _remove_stale_temp_files(output_dir: Path, document_id: str) -> None:
    """Delete temp files an earlier killed write left behind for this document."""
    for stale in output_dir.glob(f".{document_id}.*.tmp"):
        try:
            stale.unlink(missing_ok=True)
        except OSError:
            logger.warning("Could not remove stale temporary chunk-set file for %s", document_id)


def write_chunk_set(chunk_set: dict[str, Any], output_dir: Path, *, file_mode: int = DEFAULT_FILE_MODE) -> Path:
    """Write ``{document_id}.json`` into ``output_dir`` atomically.

    The file is written under a temporary name in the same directory, flushed to
    disk, then renamed, so a reader never sees a partial file and a crash leaves
    either the old file or the new one. Writing the same document again replaces
    its file. Temporary files that a killed earlier write left for this document
    are removed first, so no chunk text lingers in them.

    # #CRITICAL: Concurrency: the consuming application polls this directory while we write
    # #VERIFY: tests/unit/test_chunk_set.py::test_failed_write_leaves_no_partial_file and
    # test_write_creates_named_file_without_temp_leftovers (Path.replace is atomic on one filesystem;
    # the temp file lives in the target directory)
    # #ASSUME: one process at a time writes a given document, since stale temp files are swept
    # #VERIFY: run the Chunk stage as a single job per chunk directory

    Args:
        chunk_set: A set from ``build_chunk_set`` or ``build_withdrawn_chunk_set``
        output_dir: Chunk-set directory, created when missing
        file_mode: Permission bits of the written file; see ``DEFAULT_FILE_MODE``

    Returns:
        Path of the written file

    Raises:
        ChunkingError: If the set has no document ID, the ID is not a lowercase
            hyphenated UUID (it names the file, so it must not be a path), or
            ``file_mode`` is not a plain read-write mode
    """
    raw_id = chunk_set.get("document_id")
    if not raw_id:
        msg = "Chunk set has no document_id"
        raise ChunkingError(msg)
    document_id = _require_uuid(raw_id, "document_id")
    if document_id != raw_id:
        msg = "document_id must be a lowercase hyphenated UUID"
        raise ChunkingError(msg)
    if file_mode & ~0o666 or file_mode & 0o600 != 0o600:
        msg = "file_mode must include owner read and write and no execute or special bits"
        raise ChunkingError(msg)

    output_dir.mkdir(parents=True, exist_ok=True)
    target = _chunk_set_path(output_dir, document_id)
    payload = json.dumps(chunk_set, indent=2, ensure_ascii=False) + "\n"
    _remove_stale_temp_files(output_dir, document_id)

    fd, tmp_name = tempfile.mkstemp(dir=output_dir, prefix=f".{document_id}.", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        tmp_path.chmod(file_mode)
        tmp_path.replace(target)  # atomic on one filesystem
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
    _fsync_directory(output_dir)
    return target
