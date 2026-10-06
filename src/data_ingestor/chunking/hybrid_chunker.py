"""Structure-aware chunking with docling-core HybridChunker.

Chunks follow the document tree (headings, tables, lists), are split further
when they exceed the token budget, and merge small neighbours. Token counts use
a Hugging Face tokenizer chosen by the consuming application, so the cap is a
real cap for the embedder that application will run. This stage never embeds and
does not record an embedding model: that belongs to the consumer.

Importing this module loads docling-core and transformers, which takes seconds.
``data_ingestor.chunking`` therefore re-exports it lazily.
"""

import logging
import warnings
from typing import Any, Self

from docling_core.transforms.chunker.hierarchical_chunker import DocChunk
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.transforms.chunker.tokenizer.base import BaseTokenizer
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from docling_core.types.doc import DoclingDocument
from transformers import AutoTokenizer

from data_ingestor.core.config import Settings
from data_ingestor.core.exceptions import ChunkingError
from data_ingestor.core.metadata_keys import DOCLING_JSON_KEY
from data_ingestor.core.models import Chunk, Document

logger = logging.getLogger(__name__)

# Document-level fields copied onto every chunk. Values come from Document.metadata.
DOCUMENT_METADATA_FIELDS = (
    "sha256",
    "entity_id",
    "document_type",
    "category",
    "is_confidential",
    "consent_on_file",
    "title",
    "document_date",
)

# Fields whose absence must stop chunking: a missing consent or confidentiality flag
# must never become a silent None that a downstream filter reads as "not restricted".
_REQUIRED_TEXT_FIELDS = ("sha256", "entity_id")
_REQUIRED_FLAG_FIELDS = ("is_confidential", "consent_on_file")

_MAX_RESPLIT_ATTEMPTS = 3
# docling-core warns with this text when headings or captions outlast the token budget.
# The warning also quotes the chunk text, so it is recorded and logged without the text.
_HEADINGS_DROPPED_MARKER = "Headers and captions for this chunk are longer"

_ChunkPiece = tuple[DocChunk, str, int]  # docling chunk, contextualized text, token count


# #ASSUME: The hub is reachable and the revision still resolves; with no revision the hub's
# default branch is followed and can change chunk boundaries between runs
# #VERIFY: Pin the revision (chunk_tokenizer_revision) wherever boundaries must be reproducible;
# tests/unit/test_hybrid_chunker.py covers loading with and without the hub
def load_tokenizer(name: str, max_tokens: int, revision: str | None = None) -> BaseTokenizer:
    """Load the Hugging Face tokenizer used to size chunks.

    Pass the tokenizer of the embedding model the consuming application will use.
    """
    return HuggingFaceTokenizer(
        tokenizer=AutoTokenizer.from_pretrained(name, revision=revision),
        max_tokens=max_tokens,
    )


class _CappedTokenizer(BaseTokenizer):
    """View of another tokenizer with a smaller token cap, used to re-split over-cap chunks."""

    base: BaseTokenizer
    cap: int

    def count_tokens(self, text: str) -> int:
        return self.base.count_tokens(text)

    def get_max_tokens(self) -> int:
        return self.cap

    def get_tokenizer(self) -> Any:
        return self.base.get_tokenizer()


# #CRITICAL: Citation Integrity: Every chunk must carry a page; a chunk without one is an error
# #VERIFY: tests/unit/test_hybrid_chunker.py::test_chunk_without_page_provenance_is_an_error
# #CRITICAL: Consent and confidentiality: chunks must never carry an unset flag or identity
# #VERIFY: tests/unit/test_hybrid_chunker.py::test_missing_or_invalid_document_metadata_is_an_error
class HybridDocumentChunker:
    """DocumentChunker backed by docling-core HybridChunker.

    Page ranges are taken from the source items of each chunk. When one item is split
    into several chunks, every part reports the item's full page range, so a split chunk
    can cite more pages than it contains text from.
    """

    def __init__(
        self,
        tokenizer: BaseTokenizer,
        merge_peers: bool = True,
    ) -> None:
        """Initialize the chunker.

        Args:
            tokenizer: Tokenizer carrying the token cap (see ``load_tokenizer``)
            merge_peers: Merge undersized sibling chunks
        """
        self._chunker = HybridChunker(tokenizer=tokenizer, merge_peers=merge_peers)
        self._tokenizer = tokenizer

    @classmethod
    def from_settings(cls, settings: Settings, merge_peers: bool = True) -> Self:
        """Build a chunker from application settings (tokenizer, revision and token cap)."""
        tokenizer = load_tokenizer(
            settings.chunk_tokenizer,
            settings.chunk_max_tokens,
            revision=settings.chunk_tokenizer_revision,
        )
        return cls(tokenizer, merge_peers=merge_peers)

    def chunk_document(self, document: Document) -> list[Chunk]:
        """Chunk a Document produced by ``docling_json_to_document``.

        Raises:
            ChunkingError: If required document metadata is missing or invalid, the
                Docling tree is missing or invalid, any chunk has no page, or a chunk
                cannot be brought under the token cap
        """
        self._require_document_metadata(document)
        docling_doc = self._load_tree(document)

        chunks: list[Chunk] = []
        for dl_chunk in self._docling_chunks(docling_doc, document.document_id):
            for piece, text, token_count in self._within_cap(docling_doc, dl_chunk):
                chunks.append(self._to_chunk(document, piece, text, token_count, index=len(chunks)))
        return chunks

    @staticmethod
    def _require_document_metadata(document: Document) -> None:
        metadata = document.metadata
        invalid = [key for key in _REQUIRED_TEXT_FIELDS if not isinstance(metadata.get(key), str) or not metadata[key]]
        invalid += [key for key in _REQUIRED_FLAG_FIELDS if not isinstance(metadata.get(key), bool)]
        if invalid:
            msg = f"Document {document.document_id} has missing or invalid metadata: {', '.join(invalid)}"
            raise ChunkingError(msg)

    @staticmethod
    def _load_tree(document: Document) -> DoclingDocument:
        raw = document.metadata.get(DOCLING_JSON_KEY)
        if not raw:
            msg = f"Document {document.document_id} carries no Docling tree to chunk"
            raise ChunkingError(msg)
        try:
            return DoclingDocument.model_validate(raw)
        except ValueError as exc:
            # The validation message can quote document text, so it is not forwarded
            msg = f"Document {document.document_id} carries an invalid Docling tree"
            raise ChunkingError(msg) from exc

    def _docling_chunks(self, docling_doc: DoclingDocument, document_id: str) -> list[DocChunk]:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            raw_chunks = list(self._chunker.chunk(dl_doc=docling_doc))

        dropped = 0
        for item in caught:
            if _HEADINGS_DROPPED_MARKER in str(item.message):
                dropped += 1
            else:
                warnings.warn_explicit(item.message, item.category, item.filename, item.lineno)
        if dropped:
            logger.warning(
                "Document %s: %d chunk(s) lost their headings or captions because those outlast the token cap",
                document_id,
                dropped,
            )

        result: list[DocChunk] = []
        for raw in raw_chunks:
            if not isinstance(raw, DocChunk):
                msg = f"Unexpected chunk type {type(raw).__name__} from HybridChunker"
                raise ChunkingError(msg)
            result.append(raw)
        return result

    def _measure(self, dl_chunk: DocChunk) -> _ChunkPiece:
        text = self._chunker.contextualize(chunk=dl_chunk)
        return dl_chunk, text, self._tokenizer.count_tokens(text)

    def _within_cap(self, docling_doc: DoclingDocument, dl_chunk: DocChunk) -> list[_ChunkPiece]:
        """Return the chunk, re-split if headings added by contextualize push it over the cap.

        docling-core splits table rows without counting the headings that contextualize
        prepends, so a large table under a long heading can exceed the cap.
        """
        piece = self._measure(dl_chunk)
        cap = self._tokenizer.get_max_tokens()
        if piece[2] <= cap:
            return [piece]

        overhead = piece[2] - self._tokenizer.count_tokens(dl_chunk.text)
        budget = cap - max(overhead, 0)
        for _ in range(_MAX_RESPLIT_ATTEMPTS):
            if budget <= 0:
                break
            capped = HybridChunker(tokenizer=_CappedTokenizer(base=self._tokenizer, cap=budget), merge_peers=False)
            serializer = capped.serializer_provider.get_serializer(doc=docling_doc)
            segments = capped.segment(dl_chunk, budget, serializer)
            pieces = [self._measure(DocChunk(text=segment, meta=dl_chunk.meta)) for segment in segments]
            worst = max(count for _, _, count in pieces)
            if worst <= cap:
                return pieces
            budget -= worst - cap

        msg = "A chunk exceeds the token cap and cannot be split under it (its headings or captions are too long)"
        raise ChunkingError(msg)

    @staticmethod
    def _to_chunk(document: Document, dl_chunk: DocChunk, text: str, token_count: int, index: int) -> Chunk:
        pages = sorted({p.page_no for item in dl_chunk.meta.doc_items for p in item.prov})
        if not pages:
            msg = f"Chunk {index} of document {document.document_id} has no page provenance"
            raise ChunkingError(msg)

        headings = dl_chunk.meta.headings or []
        metadata: dict[str, Any] = {
            "document_id": document.document_id,
            "chunk_index": index,
            "page_start": pages[0],
            "page_end": pages[-1],
            "section_title": headings[-1] if headings else None,
            "section_hierarchy": list(headings),
        }
        metadata.update({key: document.metadata.get(key) for key in DOCUMENT_METADATA_FIELDS})
        return Chunk(
            content=text,
            metadata=metadata,
            token_count=token_count,
            start_page=pages[0],
            end_page=pages[-1],
        )
