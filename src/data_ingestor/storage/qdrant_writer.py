"""Qdrant writer for document chunks.

Collections are created with two named vectors from the start. Qdrant cannot add
a sparse vector to an existing collection, so the "sparse" slot must exist at
creation even though nothing fills it yet.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from qdrant_client import QdrantClient, models

from data_ingestor.core.exceptions import StorageError
from data_ingestor.core.models import Chunk

logger = logging.getLogger(__name__)

DENSE_VECTOR = "dense"
SPARSE_VECTOR = "sparse"
DENSE_DIMENSIONS = 1024

# Namespace for deterministic point ids: same document and chunk index give the same id.
_POINT_NAMESPACE = uuid.UUID("6f1d3a52-8c4e-4b7a-9a1e-2d5f0c3b7e10")

_INDEXED_FIELDS: dict[str, models.PayloadSchemaType] = {
    "is_confidential": models.PayloadSchemaType.BOOL,
    "entity_id": models.PayloadSchemaType.KEYWORD,
    "document_id": models.PayloadSchemaType.KEYWORD,
}


def point_id(document_id: str, chunk_index: int) -> str:
    """Deterministic point id for a chunk."""
    return str(uuid.uuid5(_POINT_NAMESPACE, f"{document_id}:{chunk_index}"))


def ensure_collection(
    client: QdrantClient,
    collection: str,
    indexed_fields: dict[str, models.PayloadSchemaType] | None = None,
) -> None:
    """Create a collection with "dense" and "sparse" named vectors if it does not exist.

    # #CRITICAL: Schema: Qdrant cannot add a sparse vector to an existing collection
    # #VERIFY: Every collection is created through this function so the sparse slot always exists
    """
    if client.collection_exists(collection):
        return
    client.create_collection(
        collection_name=collection,
        vectors_config={DENSE_VECTOR: models.VectorParams(size=DENSE_DIMENSIONS, distance=models.Distance.COSINE)},
        sparse_vectors_config={SPARSE_VECTOR: models.SparseVectorParams()},
    )
    for field, schema in (indexed_fields or {}).items():
        client.create_payload_index(collection, field_name=field, field_schema=schema)
    logger.info("Created Qdrant collection %s", collection)


class QdrantChunkWriter:
    """Writes chunks and their dense vectors into one Qdrant collection."""

    def __init__(self, client: QdrantClient, collection: str) -> None:
        """Initialize the writer.

        Args:
            client: Qdrant client (server, or local mode in tests)
            collection: Collection name, taken from configuration
        """
        self._client = client
        self.collection = collection

    def ensure_collection(self) -> None:
        """Create the collection with both named vectors and payload indexes if absent."""
        ensure_collection(self._client, self.collection, _INDEXED_FIELDS)

    def delete_document(self, document_id: str) -> None:
        """Delete every point belonging to a document."""
        self._client.delete(
            collection_name=self.collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))],
                ),
            ),
            wait=True,
        )

    def replace_document(self, document_id: str, chunks: list[Chunk], vectors: list[list[float]]) -> int:
        """Delete a document's points, then index its chunks. Only the dense vector is filled.

        # #CRITICAL: Idempotency: Old points are deleted first, so re-indexing leaves one set
        # #VERIFY: Delete and upsert are two calls; a crash between them leaves the document unindexed, never doubled

        Args:
            document_id: Document the chunks belong to
            chunks: Chunks to index
            vectors: One dense vector per chunk, in the same order

        Returns:
            Number of points written

        Raises:
            StorageError: On a length or dimension mismatch
        """
        if len(chunks) != len(vectors):
            msg = f"Got {len(vectors)} vectors for {len(chunks)} chunks"
            raise StorageError(msg)
        if any(len(vector) != DENSE_DIMENSIONS for vector in vectors):
            msg = f"Every dense vector must have {DENSE_DIMENSIONS} dimensions"
            raise StorageError(msg)

        self.delete_document(document_id)
        if not chunks:
            return 0

        embedded_at = datetime.now(UTC).isoformat()
        points = [
            models.PointStruct(
                id=point_id(document_id, index),
                vector={DENSE_VECTOR: vector},
                payload=self._payload(chunk, document_id, embedded_at),
            )
            for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))
        ]
        self._client.upsert(collection_name=self.collection, points=points, wait=True)
        return len(points)

    @staticmethod
    def _payload(chunk: Chunk, document_id: str, embedded_at: str) -> dict[str, Any]:
        payload = dict(chunk.metadata)
        payload["document_id"] = document_id
        payload["text"] = chunk.content
        payload["embedded_at"] = embedded_at
        return payload
