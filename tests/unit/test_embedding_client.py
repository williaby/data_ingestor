"""Tests for EmbeddingClient against a fake embeddings server."""

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest

from data_ingestor.core.exceptions import EmbeddingError
from data_ingestor.core.models import Chunk
from data_ingestor.embedding import QUERY_PREFIX, EmbeddingClient
from tests.fake_embedding_server import TEST_KEY, FakeEmbeddingServer, fake_vector, running_fake_embedding_server

MODEL = "test-embed-model"


@pytest.fixture
def server() -> Iterator[FakeEmbeddingServer]:
    with running_fake_embedding_server() as fake:
        yield fake


def _client(server: FakeEmbeddingServer, key: str = TEST_KEY, batch_size: int = 32) -> EmbeddingClient:
    return EmbeddingClient(base_url=server.url, api_key=key, model=MODEL, batch_size=batch_size)


def test_query_prefix_is_exact() -> None:
    assert QUERY_PREFIX.endswith("\nQuery:")
    assert QUERY_PREFIX.startswith("Instruct: Given a question about a family's financial, estate and tax documents")
    assert "\\n" not in QUERY_PREFIX  # a real newline, not a backslash and n


def test_query_gets_prefix_appended_without_space(server: FakeEmbeddingServer) -> None:
    vector = _client(server).embed_query("what is the deadline")
    sent = server.requests[0]["body"]["input"]
    assert sent == f"{QUERY_PREFIX}what is the deadline"
    assert "Query:what" in sent
    assert len(vector) == 1024


def test_documents_get_no_prefix_and_keep_order(server: FakeEmbeddingServer) -> None:
    texts = ["alpha beta", "gamma delta", "epsilon"]
    vectors = _client(server).embed_documents(texts)
    assert server.requests[0]["body"]["input"] == texts
    assert vectors == [fake_vector(t) for t in texts]


def test_request_shape_and_bearer_header(server: FakeEmbeddingServer) -> None:
    _client(server).embed_documents(["one"])
    request = server.requests[0]
    assert request["path"] == "/v1/embeddings"
    assert request["auth"] == f"Bearer {TEST_KEY}"
    assert request["body"]["model"] == MODEL
    assert request["body"]["input"] == "one"  # a single text is sent as a string


def test_batches_by_batch_size(server: FakeEmbeddingServer) -> None:
    vectors = _client(server, batch_size=2).embed_documents(["a", "b", "c", "d", "e"])
    assert len(vectors) == 5
    assert len(server.requests) == 3


def test_empty_input_makes_no_request(server: FakeEmbeddingServer) -> None:
    assert _client(server).embed_documents([]) == []
    assert server.requests == []


def test_wrong_key_is_an_error(server: FakeEmbeddingServer) -> None:
    with pytest.raises(EmbeddingError, match="401"):
        _client(server, key="wrong").embed_query("q")


def test_server_error_does_not_leak_input_text(server: FakeEmbeddingServer) -> None:
    server.fail_with = 500
    with pytest.raises(EmbeddingError) as excinfo:
        _client(server).embed_documents(["confidential passage text"])
    assert "confidential" not in str(excinfo.value)


def test_wrong_dimensions_is_an_error(server: FakeEmbeddingServer) -> None:
    server.dimensions = 768
    with pytest.raises(EmbeddingError, match="1024"):
        _client(server).embed_query("q")


def test_connection_failure_is_an_error(server: FakeEmbeddingServer) -> None:
    client = _client(server)
    server.stop()
    with pytest.raises(EmbeddingError):
        client.embed_query("q")


def test_embed_chunks_stamps_embedded_at_on_every_chunk(server: FakeEmbeddingServer) -> None:
    chunks = [Chunk(content="alpha beta"), Chunk(content="gamma delta")]
    before = datetime.now(UTC)
    vectors = _client(server).embed_chunks(chunks)
    after = datetime.now(UTC)

    assert vectors == [fake_vector(chunk.content) for chunk in chunks]
    stamps = {chunk.metadata["embedded_at"] for chunk in chunks}
    assert len(stamps) == 1
    stamped = datetime.fromisoformat(stamps.pop())
    assert stamped.utcoffset() is not None
    assert before <= stamped <= after


def test_embed_chunks_does_not_stamp_when_the_request_fails(server: FakeEmbeddingServer) -> None:
    chunk = Chunk(content="alpha beta")
    with pytest.raises(EmbeddingError):
        _client(server, key="wrong-key").embed_chunks([chunk])
    assert "embedded_at" not in chunk.metadata


def test_embed_chunks_of_nothing_is_empty(server: FakeEmbeddingServer) -> None:
    assert _client(server).embed_chunks([]) == []
