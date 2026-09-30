"""Shared fixtures for unit tests.

Qdrant client fixtures:

By default tests run against qdrant-client local mode (in-process). To run the same
tests against a disposable Qdrant container, set DATA_INGESTOR_TEST_QDRANT_URL.
"""

import os
import uuid
from collections.abc import Iterator

import pytest
from qdrant_client import QdrantClient


@pytest.fixture
def qdrant_client() -> Iterator[QdrantClient]:
    url = os.environ.get("DATA_INGESTOR_TEST_QDRANT_URL")
    client = QdrantClient(url=url) if url else QdrantClient(":memory:")
    yield client
    client.close()


@pytest.fixture
def collection_name() -> str:
    """Unique per test so a shared container is never polluted across tests."""
    return f"test-{uuid.uuid4().hex[:12]}"
