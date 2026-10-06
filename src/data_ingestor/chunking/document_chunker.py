"""Interface shared by document chunkers."""

from typing import Protocol

from data_ingestor.core.models import Chunk, Document


class DocumentChunker(Protocol):
    """Splits a Document into chunks.

    The protocol fixes the call signature only. Implementations differ in what they
    require of the Document and in what they guarantee about each Chunk, so check the
    implementation before swapping one for another:

    - ``HybridDocumentChunker`` needs a Document built by ``docling_json_to_document``
      (it reads the stored Docling tree), requires valid ``sha256``, ``entity_id``,
      ``is_confidential`` and ``consent_on_file`` metadata, raises ``ChunkingError``
      for any chunk without a page, and copies the document metadata fields onto every
      chunk.
    - ``ByTitleChunker`` works from the flat element list and makes none of those
      checks or guarantees.
    """

    def chunk_document(self, document: Document) -> list[Chunk]:
        """Return the chunks for ``document``."""
