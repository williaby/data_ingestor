"""Dense search over the family-docs and tax-law collections.

The confidentiality and entity filters are part of the Qdrant query itself. They
are never applied to results after they come back.
"""

import logging
from typing import Literal, get_args
from uuid import UUID

from pydantic import BaseModel, Field
from qdrant_client import QdrantClient, models

from data_ingestor.embedding import EmbeddingClient

logger = logging.getLogger(__name__)

DENSE_VECTOR = "dense"
DEFAULT_TOP_K = 8
MAX_TOP_K = 8  # dense search only, no reranker; callers cannot ask for more

CollectionName = Literal["family-docs", "tax-law"]


class SearchRequest(BaseModel):
    """Body of POST /api/v1/search."""

    query: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=DEFAULT_TOP_K, ge=1)
    include_confidential: bool = False
    entity_ids: list[UUID] | None = None
    collections: list[CollectionName] = Field(default_factory=lambda: list(get_args(CollectionName)), min_length=1)


class FamilyCitation(BaseModel):
    """Where a family-docs chunk came from."""

    document_id: str | None
    title: str | None
    entity_id: str | None
    document_date: str | None
    page_start: int | None
    page_end: int | None
    section: str | None


class TaxLawCitation(BaseModel):
    """Which tax-law subtopic a result came from."""

    id: str | None
    title: str | None


class SearchResult(BaseModel):
    """One returned chunk. ``text`` is plain data; nothing in it is interpreted."""

    text: str
    score: float
    collection: CollectionName
    citation: FamilyCitation | TaxLawCitation


class SearchResponse(BaseModel):
    """Body returned by POST /api/v1/search."""

    results: list[SearchResult]
    embedding_model: str


def family_filter(include_confidential: bool, entity_ids: list[UUID] | None) -> models.Filter | None:
    """Payload filter for family-docs, evaluated inside the Qdrant query.

    # #CRITICAL: Confidentiality: This filter is the only barrier; results are never filtered afterwards
    # #VERIFY: A chunk missing the is_confidential field never matches, so unlabeled data fails closed
    """
    must: list[models.Condition] = []
    if not include_confidential:
        must.append(models.FieldCondition(key="is_confidential", match=models.MatchValue(value=False)))
    if entity_ids:
        must.append(models.FieldCondition(key="entity_id", match=models.MatchAny(any=[str(e) for e in entity_ids])))
    return models.Filter(must=must) if must else None


class SearchService:
    """Embeds a query and runs dense search across the requested collections."""

    def __init__(
        self,
        client: QdrantClient,
        embedder: EmbeddingClient,
        collections: dict[CollectionName, str],
        embedding_model: str,
    ) -> None:
        """Initialize the service.

        Args:
            client: Qdrant client
            embedder: Embedding client, used for the query only
            collections: Mapping from API collection name to configured Qdrant collection
            embedding_model: Model name reported in responses
        """
        self._client = client
        self._embedder = embedder
        self._collections = collections
        self.embedding_model = embedding_model

    def search(self, request: SearchRequest) -> SearchResponse:
        """Run the search and merge results by score."""
        limit = min(request.top_k, MAX_TOP_K)
        vector = self._embedder.embed_query(request.query)

        results: list[SearchResult] = []
        for name in dict.fromkeys(request.collections):
            collection = self._collections[name]
            if not self._client.collection_exists(collection):
                logger.warning("Collection %s does not exist; skipping", collection)
                continue
            query_filter = (
                family_filter(request.include_confidential, request.entity_ids) if name == "family-docs" else None
            )
            response = self._client.query_points(
                collection_name=collection,
                query=vector,
                using=DENSE_VECTOR,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            )
            results.extend(_to_result(name, point) for point in response.points)

        results.sort(key=lambda result: result.score, reverse=True)
        return SearchResponse(results=results[:limit], embedding_model=self.embedding_model)


def _to_result(name: CollectionName, point: models.ScoredPoint) -> SearchResult:
    payload = point.payload or {}
    citation: FamilyCitation | TaxLawCitation
    if name == "tax-law":
        citation = TaxLawCitation(id=payload.get("id"), title=payload.get("title"))
    else:
        citation = FamilyCitation(
            document_id=payload.get("document_id"),
            title=payload.get("title"),
            entity_id=payload.get("entity_id"),
            document_date=payload.get("document_date"),
            page_start=payload.get("page_start"),
            page_end=payload.get("page_end"),
            section=payload.get("section_title"),
        )
    return SearchResult(text=str(payload.get("text", "")), score=point.score, collection=name, citation=citation)
