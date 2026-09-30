"""Structure-aware chunking with docling-core HybridChunker.

Chunks follow the document tree (headings, tables, lists), are split further
when they exceed the token budget, and merge small neighbours. Token counts use
the tokenizer of the embedding model so the cap is a real cap for the embedder.
"""

import logging
from typing import Any

from docling_core.transforms.chunker.hierarchical_chunker import DocChunk
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.transforms.chunker.tokenizer.base import BaseTokenizer
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from docling_core.types.doc import DoclingDocument

from data_ingestor.conversion.docling_mapper import DOCLING_JSON_KEY
from data_ingestor.core.exceptions import ChunkingError
from data_ingestor.core.models import Chunk, Document

logger = logging.getLogger(__name__)

# Document-level fields copied onto every chunk. Values come from Document.metadata.
DOCUMENT_METADATA_FIELDS = (
    "sha256",
    "entity_id",
    "document_type",
    "category",
    "is_confidential",
    "title",
    "document_date",
)


def load_embedding_tokenizer(name: str, max_tokens: int) -> BaseTokenizer:
    """Load the Hugging Face tokenizer that matches the embedding model."""
    from transformers import AutoTokenizer  # noqa: PLC0415  (heavy import, only needed at construction)

    return HuggingFaceTokenizer(tokenizer=AutoTokenizer.from_pretrained(name), max_tokens=max_tokens)


class HybridDocumentChunker:
    """DocumentChunker backed by docling-core HybridChunker.

    # #CRITICAL: Citation Integrity: Every chunk must carry a page; a chunk without one is an error
    # #VERIFY: tests/unit/test_hybrid_chunker.py fails if any chunk lacks a page
    """

    def __init__(
        self,
        tokenizer: BaseTokenizer,
        embedding_model: str,
        merge_peers: bool = True,
    ) -> None:
        """Initialize the chunker.

        Args:
            tokenizer: Tokenizer matching the embedding model, carrying the token cap
            embedding_model: Embedding model name recorded on every chunk
            merge_peers: Merge undersized sibling chunks
        """
        self._chunker = HybridChunker(tokenizer=tokenizer, merge_peers=merge_peers)
        self._tokenizer = tokenizer
        self.embedding_model = embedding_model

    def chunk_document(self, document: Document) -> list[Chunk]:
        """Chunk a Document produced by ``docling_json_to_document``.

        Raises:
            ChunkingError: If the Docling tree is missing, or any chunk has no page
        """
        raw = document.metadata.get(DOCLING_JSON_KEY)
        if not raw:
            msg = f"Document {document.document_id} carries no Docling tree to chunk"
            raise ChunkingError(msg)
        docling_doc = DoclingDocument.model_validate(raw)

        chunks: list[Chunk] = []
        for index, dl_chunk in enumerate(self._chunker.chunk(dl_doc=docling_doc)):
            if not isinstance(dl_chunk, DocChunk):
                msg = f"Unexpected chunk type {type(dl_chunk).__name__} from HybridChunker"
                raise ChunkingError(msg)
            pages = sorted({p.page_no for item in dl_chunk.meta.doc_items for p in item.prov})
            if not pages:
                msg = f"Chunk {index} of document {document.document_id} has no page provenance"
                raise ChunkingError(msg)

            text = self._chunker.contextualize(chunk=dl_chunk)
            headings = dl_chunk.meta.headings or []
            metadata: dict[str, Any] = {
                "document_id": document.document_id,
                "chunk_index": index,
                "page_start": pages[0],
                "page_end": pages[-1],
                "section_title": headings[-1] if headings else None,
                "embedding_model": self.embedding_model,
            }
            metadata.update({key: document.metadata.get(key) for key in DOCUMENT_METADATA_FIELDS})

            chunks.append(
                Chunk(
                    content=text,
                    metadata=metadata,
                    token_count=self._tokenizer.count_tokens(text),
                    start_page=pages[0],
                    end_page=pages[-1],
                ),
            )
        return chunks
