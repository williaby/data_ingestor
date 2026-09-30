"""Tests for QdrantChunkWriter (qdrant-client local mode unless a test server URL is set)."""

import pytest
from qdrant_client import QdrantClient, models

from data_ingestor.core.exceptions import StorageError
from data_ingestor.core.models import Chunk
from data_ingestor.storage.qdrant_writer import DENSE_DIMENSIONS, QdrantChunkWriter


def _chunk(document_id: str, index: int, **extra: object) -> Chunk:
    metadata = {"document_id": document_id, "chunk_index": index, "is_confidential": False, "entity_id": "e1"}
    metadata.update(extra)
    return Chunk(content=f"text {document_id} {index}", metadata=metadata, start_page=1, end_page=1)


def _vector(seed: float = 1.0) -> list[float]:
    return [seed] + [0.0] * (DENSE_DIMENSIONS - 1)


def _count(client: QdrantClient, collection: str, document_id: str) -> int:
    return client.count(
        collection,
        count_filter=models.Filter(
            must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))],
        ),
    ).count


@pytest.fixture
def writer(qdrant_client: QdrantClient, collection_name: str) -> QdrantChunkWriter:
    writer = QdrantChunkWriter(qdrant_client, collection_name)
    writer.ensure_collection()
    return writer


def test_collection_has_dense_and_sparse_slots(
    writer: QdrantChunkWriter,
    qdrant_client: QdrantClient,
) -> None:
    params = qdrant_client.get_collection(writer.collection).config.params
    assert params.vectors["dense"].size == 1024  # type: ignore[index]
    assert params.vectors["dense"].distance == models.Distance.COSINE  # type: ignore[index]
    assert params.sparse_vectors is not None
    assert "sparse" in params.sparse_vectors


def test_ensure_collection_is_idempotent(writer: QdrantChunkWriter) -> None:
    writer.ensure_collection()  # must not raise or recreate


def test_only_dense_is_filled(writer: QdrantChunkWriter, qdrant_client: QdrantClient) -> None:
    writer.replace_document("d1", [_chunk("d1", 0)], [_vector()])
    points, _ = qdrant_client.scroll(writer.collection, with_vectors=True, with_payload=True)
    (point,) = points
    assert set(point.vector) == {"dense"}  # type: ignore[arg-type]
    assert point.payload["text"] == "text d1 0"  # type: ignore[index]
    assert point.payload["embedded_at"]  # type: ignore[index]


def test_reindexing_leaves_one_set_of_points(
    writer: QdrantChunkWriter,
    qdrant_client: QdrantClient,
) -> None:
    chunks = [_chunk("d1", 0), _chunk("d1", 1), _chunk("d1", 2)]
    writer.replace_document("d1", chunks, [_vector()] * 3)
    writer.replace_document("d1", chunks, [_vector()] * 3)
    assert _count(qdrant_client, writer.collection, "d1") == 3


def test_reindexing_removes_stale_chunks(writer: QdrantChunkWriter, qdrant_client: QdrantClient) -> None:
    writer.replace_document("d1", [_chunk("d1", i) for i in range(4)], [_vector()] * 4)
    writer.replace_document("d1", [_chunk("d1", 0)], [_vector()])
    assert _count(qdrant_client, writer.collection, "d1") == 1


def test_other_documents_are_untouched(writer: QdrantChunkWriter, qdrant_client: QdrantClient) -> None:
    writer.replace_document("d1", [_chunk("d1", 0)], [_vector()])
    writer.replace_document("d2", [_chunk("d2", 0)], [_vector()])
    writer.replace_document("d1", [_chunk("d1", 0)], [_vector()])
    assert _count(qdrant_client, writer.collection, "d2") == 1


def test_rejects_wrong_dimensions_and_length(writer: QdrantChunkWriter) -> None:
    with pytest.raises(StorageError):
        writer.replace_document("d1", [_chunk("d1", 0)], [[0.1, 0.2]])
    with pytest.raises(StorageError):
        writer.replace_document("d1", [_chunk("d1", 0)], [])
