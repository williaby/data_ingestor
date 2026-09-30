"""Tests for the tax-law indexer, using a small made-up knowledge base."""

import json
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from qdrant_client import QdrantClient

from data_ingestor.core.exceptions import StorageError
from data_ingestor.embedding import EmbeddingClient
from data_ingestor.indexing import index_tax_law, load_knowledge_base
from tests.fake_embedding_server import TEST_KEY, running_fake_embedding_server

FIXTURE = Path(__file__).parent.parent / "fixtures" / "tax_law_sample.json"


@pytest.fixture
def embedder() -> Iterator[EmbeddingClient]:
    with running_fake_embedding_server() as server:
        yield EmbeddingClient(base_url=server.url, api_key=TEST_KEY, model="test-embed-model")


def _points(client: QdrantClient, collection: str) -> list:
    points, _ = client.scroll(collection, limit=100, with_payload=True, with_vectors=True)
    return points


def test_one_point_per_non_empty_subtopic(
    qdrant_client: QdrantClient, collection_name: str, embedder: EmbeddingClient,
) -> None:
    count = index_tax_law(FIXTURE, qdrant_client, embedder, collection_name)
    points = _points(qdrant_client, collection_name)
    assert count == len(points) == 3  # the blank subtopic is skipped
    by_id = {p.payload["id"]: p.payload for p in points}
    assert set(by_id) == {"widgets-basic", "widgets-limits", "gadgets-basic"}
    assert by_id["widgets-basic"]["title"] == "Basic widget credit"
    assert by_id["widgets-basic"]["topic"] == "Widget Credits"
    assert by_id["gadgets-basic"]["topic"] == "Gadget Deductions"
    assert "widget" in by_id["widgets-basic"]["text"]


def test_collection_has_dense_and_sparse_slots_and_only_dense_is_filled(
    qdrant_client: QdrantClient,
    collection_name: str,
    embedder: EmbeddingClient,
) -> None:
    index_tax_law(FIXTURE, qdrant_client, embedder, collection_name)
    params = qdrant_client.get_collection(collection_name).config.params
    assert params.vectors["dense"].size == 1024  # type: ignore[index]
    assert "sparse" in (params.sparse_vectors or {})
    assert all(set(p.vector) == {"dense"} for p in _points(qdrant_client, collection_name))


def test_reindexing_is_idempotent_and_drops_removed_subtopics(
    qdrant_client: QdrantClient,
    collection_name: str,
    embedder: EmbeddingClient,
    tmp_path: Path,
) -> None:
    working = tmp_path / "kb.json"
    shutil.copy(FIXTURE, working)
    index_tax_law(working, qdrant_client, embedder, collection_name)
    index_tax_law(working, qdrant_client, embedder, collection_name)
    assert len(_points(qdrant_client, collection_name)) == 3

    data = json.loads(working.read_text())
    data["knowledgeBase"][0]["subtopics"].pop()  # remove "widgets-limits"
    working.write_text(json.dumps(data))
    index_tax_law(working, qdrant_client, embedder, collection_name)
    assert {p.payload["id"] for p in _points(qdrant_client, collection_name)} == {"widgets-basic", "gadgets-basic"}


def test_indexed_points_are_found_by_a_search_vector(
    qdrant_client: QdrantClient,
    collection_name: str,
    embedder: EmbeddingClient,
) -> None:
    index_tax_law(FIXTURE, qdrant_client, embedder, collection_name)
    vector = embedder.embed_documents(["Gadget deduction basics\nGadget expenses are deductible"])[0]
    top = qdrant_client.query_points(collection_name, query=vector, using="dense", limit=1, with_payload=True).points[0]
    assert top.payload["id"] == "gadgets-basic"


def test_missing_file_is_a_storage_error(tmp_path: Path) -> None:
    with pytest.raises(StorageError):
        load_knowledge_base(tmp_path / "absent.json")


def test_malformed_file_is_a_storage_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"knowledgeBase": [{"id": "t"}]}')
    with pytest.raises(StorageError):
        load_knowledge_base(bad)


def test_duplicate_subtopic_ids_are_rejected(tmp_path: Path) -> None:
    dup = tmp_path / "dup.json"
    sub = {"id": "same", "title": "T", "content": "C"}
    dup.write_text(json.dumps({"knowledgeBase": [{"id": "t", "topic": "X", "subtopics": [sub, sub]}]}))
    with pytest.raises(StorageError, match="duplicate"):
        load_knowledge_base(dup)
