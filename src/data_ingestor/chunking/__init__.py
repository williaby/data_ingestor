"""Chunking strategies for document segmentation.

``HybridDocumentChunker`` and ``load_tokenizer`` are re-exported lazily: importing them
loads docling-core and transformers (seconds), which users of the other chunkers and
the CLI should not pay for.
"""

from typing import TYPE_CHECKING, Any

from data_ingestor.chunking.by_title_chunker import ByTitleChunker, ChunkingStrategy
from data_ingestor.chunking.document_chunker import DocumentChunker
from data_ingestor.chunking.token_chunker import TokenChunker

if TYPE_CHECKING:
    from data_ingestor.chunking.hybrid_chunker import HybridDocumentChunker, load_tokenizer

__all__ = [
    "ByTitleChunker",
    "ChunkingStrategy",
    "DocumentChunker",
    "HybridDocumentChunker",
    "TokenChunker",
    "load_tokenizer",
]

_LAZY_EXPORTS = frozenset({"HybridDocumentChunker", "load_tokenizer"})


def __getattr__(name: str) -> Any:
    if name in _LAZY_EXPORTS:
        from data_ingestor.chunking import hybrid_chunker

        return getattr(hybrid_chunker, name)
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
