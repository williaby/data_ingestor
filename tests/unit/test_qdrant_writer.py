"""Tests for QdrantChunkWriter (qdrant-client local mode unless a test server URL is set)."""

import pytest
from qdrant_client import QdrantClient, models

from data_ingestor.core.exceptions import StorageError
from data_ingestor.core.models import EMBEDDED_AT_KEY, Chunk
from data_ingestor.embedding import EmbeddingClient
from data_ingestor.storage.qdrant_writer import DENSE_DIMENSIONS, QdrantChunkWriter
from tests.fake_embedding_server import TEST_KEY, running_fake_embedding_server


def _chunk(document_id: str, index: int, **extra: object) -> Chunk:
    metadata = {
        "document_id": document_id,
        "chunk_index": index,
        "is_confidential": False,
        "entity_id": "e1",
        EMBEDDED_AT_KEY: f"2024-05-01T10:00:0{index % 10}+00:00",
    }
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


def test_payload_carries_the_chunk_embedded_at(writer: QdrantChunkWriter, qdrant_client: QdrantClient) -> None:
    chunks = [_chunk("d1", 0), _chunk("d1", 1, embedded_at="2023-01-02T03:04:05+00:00")]
    writer.replace_document("d1", chunks, [_vector()] * 2)
    points, _ = qdrant_client.scroll(writer.collection, with_payload=True)
    stored = {point.payload["chunk_index"]: point.payload["embedded_at"] for point in points}  # type: ignore[index]
    assert stored == {0: chunks[0].metadata["embedded_at"], 1: "2023-01-02T03:04:05+00:00"}


def test_chunk_without_embedded_at_is_rejected_and_nothing_is_deleted(
    writer: QdrantChunkWriter,
    qdrant_client: QdrantClient,
) -> None:
    writer.replace_document("d1", [_chunk("d1", 0)], [_vector()])
    unembedded = Chunk(content="no timestamp", metadata={"document_id": "d1", "chunk_index": 0})
    with pytest.raises(StorageError, match="embedded_at"):
        writer.replace_document("d1", [unembedded], [_vector()])
    assert _count(qdrant_client, writer.collection, "d1") == 1


def test_embedded_chunks_round_trip_their_timestamp_into_the_payload(
    writer: QdrantChunkWriter,
    qdrant_client: QdrantClient,
) -> None:
    chunks = [Chunk(content="alpha beta", metadata={"document_id": "d1", "chunk_index": 0})]
    with running_fake_embedding_server() as server:
        embedder = EmbeddingClient(base_url=server.url, api_key=TEST_KEY, model="test-embed-model")
        vectors = embedder.embed_chunks(chunks)
    writer.replace_document("d1", chunks, vectors)

    (point,), _ = qdrant_client.scroll(writer.collection, with_payload=True)
    assert chunks[0].metadata[EMBEDDED_AT_KEY]
    assert point.payload[EMBEDDED_AT_KEY] == chunks[0].metadata[EMBEDDED_AT_KEY]  # type: ignore[index]
