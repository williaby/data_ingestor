"""Interface shared by every document chunker."""

from typing import Protocol

from data_ingestor.core.models import Chunk, Document


class DocumentChunker(Protocol):
    """Splits a Document into chunks.

    Callers depend only on this protocol, so ``HybridDocumentChunker`` and
    ``ByTitleChunker`` are interchangeable behind it.
    """

    def chunk_document(self, document: Document) -> list[Chunk]:
        """Return the chunks for ``document``."""
