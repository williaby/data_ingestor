"""Chunk-set output: the RAGChunkSet.json the Chunk stage hands to applications.

The shape follows ``chunk-embed-contract.md`` (version 1.1) in
image-preprocessing-detector. The stage ends here: it writes files and does not
embed, store vectors, or search. An application reads the directory.
"""

import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

import tiktoken

from data_ingestor.core.exceptions import ChunkingError
from data_ingestor.core.models import Chunk

SCHEMA_VERSION = "1.1"
SOURCE_TRACK = "document"
TOKEN_ENCODING = "cl100k_base"  # noqa: S105 - a tiktoken encoding name, not a secret; the contract fixes this encoding, whatever tokenizer sized the chunks

# Fixed namespace so the same document always produces the same chunk and trace IDs.
_ID_NAMESPACE = uuid.UUID("5d0c4f7e-3a51-4d0e-9a53-6b1b6a0f2c11")

# Document-level fields every chunk carries (C-5 additions the portal needs).
CARRIED_FIELDS = (
    "entity_id",
    "document_type",
    "category",
    "is_confidential",
    "title",
    "document_date",
    "sha256",
)


def _require_uuid(value: str, name: str) -> str:
    try:
        return str(uuid.UUID(value))
    except ValueError as exc:
        msg = f"{name} must be a UUID"
        raise ChunkingError(msg) from exc


def build_chunk_set(
    document_id: str,
    chunks: list[Chunk],
    chunk_strategy: str,
    trace_id: str | None = None,
) -> dict[str, Any]:
    """Build a RAGChunkSet dictionary from chunks.

    ``trust_score``, ``ocr_engine_provenance`` and ``hallucination_risk`` are
    ``None`` (JSON null): this stage has no scoring yet, and null means "not
    scored", never zero or one (D-32).

    # #CRITICAL: Citation Integrity: every chunk needs a page range; a chunk without one fails
    # #VERIFY: tests/unit/test_chunk_set.py::test_chunk_without_page_fails

    Args:
        document_id: Stable document UUID (from the document store)
        chunks: Chunks in document order
        chunk_strategy: Strategy name written on the set and on every chunk
        trace_id: Pipeline trace UUID. When absent, one is derived from the
            document ID so output stays reproducible.

    Raises:
        ChunkingError: If an ID is not a UUID or a chunk has no page range
    """
    document_id = _require_uuid(document_id, "document_id")
    trace_id = (
        _require_uuid(trace_id, "trace_id") if trace_id else str(uuid.uuid5(_ID_NAMESPACE, f"trace:{document_id}"))
    )
    encoding = tiktoken.get_encoding(TOKEN_ENCODING)

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
        entry.update({key: chunk.metadata.get(key) for key in CARRIED_FIELDS})
        entries.append(entry)

    return {
        "schema_version": SCHEMA_VERSION,
        "document_id": document_id,
        "trace_id": trace_id,
        "source_track": SOURCE_TRACK,
        "chunk_strategy": chunk_strategy,
        "total_chunks": len(entries),
        "chunks": entries,
    }


def write_chunk_set(chunk_set: dict[str, Any], output_dir: Path) -> Path:
    """Write ``{document_id}.json`` into ``output_dir`` atomically.

    The file is written under a temporary name in the same directory, then
    renamed, so a reader never sees a partial file. Writing the same document
    again replaces its file.

    # #CRITICAL: Concurrency: the consuming application polls this directory while we write
    # #VERIFY: Path.replace is atomic on one filesystem; the temp file lives in the target directory

    Raises:
        ChunkingError: If the set has no document ID
    """
    document_id = chunk_set.get("document_id")
    if not document_id:
        msg = "Chunk set has no document_id"
        raise ChunkingError(msg)

    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{document_id}.json"
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
