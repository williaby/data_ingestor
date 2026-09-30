"""Index a tax-law knowledge base into its own collection, one point per subtopic.

Expected file shape::

    {"knowledgeBase": [{"id": ..., "topic": ..., "subtopics": [{"id": ..., "title": ..., "content": ...}]}]}

The file lives outside this repository and its path comes from configuration.
"""

import json
import logging
import sys
import uuid
from pathlib import Path

from pydantic import BaseModel, ValidationError
from qdrant_client import QdrantClient, models

from data_ingestor.core.config import Settings
from data_ingestor.core.exceptions import StorageError
from data_ingestor.embedding import EmbeddingClient
from data_ingestor.storage.qdrant_writer import DENSE_VECTOR, ensure_collection

logger = logging.getLogger(__name__)

_POINT_NAMESPACE = uuid.UUID("2b9c7e64-51a0-4d38-b6f2-8e3a9d41c7f5")


class Subtopic(BaseModel):
    """One indexable unit of the knowledge base."""

    id: str
    title: str
    content: str


class Topic(BaseModel):
    """A topic grouping several subtopics."""

    id: str
    topic: str
    subtopics: list[Subtopic]


class KnowledgeBase(BaseModel):
    """Root of the knowledge-base file."""

    knowledgeBase: list[Topic]  # noqa: N815  (field name is fixed by the file format)


def load_knowledge_base(path: Path) -> KnowledgeBase:
    """Read and validate the knowledge-base file.

    Raises:
        StorageError: If the file is missing, unreadable, malformed, or has duplicate subtopic ids
    """
    try:
        knowledge_base = KnowledgeBase.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, ValidationError) as exc:
        msg = f"Cannot load knowledge base from {path.name}: {type(exc).__name__}"
        raise StorageError(msg) from exc

    ids = [sub.id for topic in knowledge_base.knowledgeBase for sub in topic.subtopics]
    if len(ids) != len(set(ids)):
        msg = "Knowledge base contains duplicate subtopic ids"
        raise StorageError(msg)
    return knowledge_base


def _point_id(subtopic_id: str) -> str:
    return str(uuid.uuid5(_POINT_NAMESPACE, subtopic_id))


def index_tax_law(path: Path, client: QdrantClient, embedder: EmbeddingClient, collection: str) -> int:
    """Index every non-empty subtopic, replacing whatever the collection held before.

    Payload per point: id, title, topic, and text (the content, returned by search).
    Points for subtopics that are no longer in the file are removed.

    Returns:
        Number of points now in the collection from this run
    """
    knowledge_base = load_knowledge_base(path)
    entries = [
        (topic.topic, sub) for topic in knowledge_base.knowledgeBase for sub in topic.subtopics if sub.content.strip()
    ]

    ensure_collection(client, collection)
    vectors = embedder.embed_documents([f"{sub.title}\n{sub.content}" for _, sub in entries])
    points = [
        models.PointStruct(
            id=_point_id(sub.id),
            vector={DENSE_VECTOR: vector},
            payload={"id": sub.id, "title": sub.title, "topic": topic, "text": sub.content},
        )
        for (topic, sub), vector in zip(entries, vectors, strict=True)
    ]

    keep = {str(point.id) for point in points}
    stale: list[models.ExtendedPointId] = []
    offset = None
    while True:
        existing, offset = client.scroll(collection, limit=256, offset=offset, with_payload=False)
        stale.extend(point.id for point in existing if str(point.id) not in keep)
        if offset is None:
            break
    if stale:
        client.delete(collection, points_selector=models.PointIdsList(points=stale), wait=True)
    if points:
        client.upsert(collection, points=points, wait=True)
    logger.info("Indexed %d tax-law subtopics into %s", len(points), collection)
    return len(points)


def main() -> int:
    """Index the configured knowledge base. Every URL, key and path comes from settings."""
    settings = Settings()
    if settings.tax_law_path is None:
        sys.stderr.write("DATA_INGESTOR_TAX_LAW_PATH is not set\n")
        return 2
    embed_key = settings.embed_api_key.get_secret_value() if settings.embed_api_key else ""
    embedder = EmbeddingClient(
        base_url=settings.embed_base_url,
        api_key=embed_key,
        model=settings.embedding_model,
        batch_size=settings.embed_batch_size,
        timeout=settings.embed_timeout,
    )
    qdrant_key = settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None
    client = QdrantClient(url=settings.qdrant_url, api_key=qdrant_key)
    count = index_tax_law(settings.tax_law_path, client, embedder, settings.tax_law_collection)
    sys.stdout.write(f"Indexed {count} subtopics\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
