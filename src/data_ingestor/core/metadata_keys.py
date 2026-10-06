"""Document metadata keys with special handling.

Kept in ``core`` so exporters can recognise internal keys without importing the
conversion stack (and its heavy dependencies).
"""

# Key under which the original Docling tree travels with a Document, so structure-aware
# chunkers (HybridChunker) can read it. It is an internal carrier, not exportable metadata.
DOCLING_JSON_KEY = "docling_json"

# Keys that exporters must never write out (large, internal, or derived from the full document).
INTERNAL_METADATA_KEYS = frozenset({DOCLING_JSON_KEY})
