"""Convert one file with docling-serve and chunk it into a chunk set."""

import hashlib
from pathlib import Path
from typing import Any

from data_ingestor.core.config import Settings
from data_ingestor.core.exceptions import ConversionError
from data_ingestor.core.models import Document, ProcessingStatus


def file_sha256(path: Path) -> str:
    """Return the SHA-256 of a file as lowercase hex."""
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def require_complete_conversion(document: Document, status: str, filename: str) -> None:
    """Refuse a document docling-serve converted only partially.

    # #CRITICAL: Data Integrity: a partial conversion may be missing content, so it is not written
    # #VERIFY: tests/unit/test_chunk_set.py::test_cli_chunk_refuses_a_partial_conversion

    Raises:
        ConversionError: If the conversion needs review
    """
    if document.status is ProcessingStatus.REQUIRES_REVIEW:
        msg = f"docling-serve reported status {status} for {filename}; review required, nothing written"
        raise ConversionError(msg)


def build_document_chunk_set(
    settings: Settings,
    file_path: Path,
    *,
    document_id: str,
    document_fields: dict[str, Any],
    trace_id: str | None = None,
) -> dict[str, Any]:
    """Convert a file with docling-serve, chunk it, and build its chunk set (nothing is written).

    Args:
        settings: Application settings (docling-serve and chunking configuration)
        file_path: The file to convert
        document_id: Document UUID
        document_fields: Document-level values carried onto every chunk
        trace_id: Pipeline trace UUID, derived from the document ID when omitted

    Returns:
        The chunk set, ready for ``write_chunk_set``

    Raises:
        ConversionError: If docling-serve fails or reports a partial conversion
        ChunkingError: If chunking fails or an ID is not a UUID
    """
    from data_ingestor.chunking import HybridDocumentChunker
    from data_ingestor.conversion import DoclingServeClient, docling_json_to_document
    from data_ingestor.export import build_chunk_set
    from data_ingestor.export.chunk_set import DEFAULT_CHUNK_STRATEGY

    with DoclingServeClient.from_settings(settings) as client:
        result = client.convert(file_path)
    document = docling_json_to_document(
        result.docling_json,
        document_id=document_id,
        filename=file_path.name,
        extra_metadata=document_fields,
        conversion_status=result.status,
    )
    require_complete_conversion(document, result.status, file_path.name)
    chunks = HybridDocumentChunker.from_settings(settings).chunk_document(document)
    return build_chunk_set(
        document_id,
        chunks,
        chunk_strategy=DEFAULT_CHUNK_STRATEGY,
        document_fields=document_fields,
        trace_id=trace_id,
    )
