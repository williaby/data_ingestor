"""Client for an OpenAI-compatible embeddings endpoint (POST /v1/embeddings).

Documents are embedded as-is. Queries get a fixed instruction prefix, which the
embedding model was trained to expect on the query side only. All embedding is
done by the remote service; no local model is loaded here.
"""

import httpx

from data_ingestor.core.exceptions import EmbeddingError

EMBEDDINGS_PATH = "/v1/embeddings"
EXPECTED_DIMENSIONS = 1024

# The text after "Query:" follows directly, with no space. The newline is a real newline.
QUERY_PREFIX = (
    "Instruct: Given a question about a family's financial, estate and tax documents, "
    "retrieve passages that answer it\nQuery:"
)


class EmbeddingClient:
    """Embeds documents and queries through the configured embedding service."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        batch_size: int = 32,
        timeout: float = 60.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        """Initialize the client.

        Args:
            base_url: Service base URL, from configuration
            api_key: Bearer key, from configuration
            model: Model name sent with each request, from configuration
            batch_size: Maximum texts per request
            timeout: Request timeout in seconds
            transport: Optional transport override, used by tests
        """
        self.model = model
        self._batch_size = batch_size
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
            transport=transport,
        )

    def close(self) -> None:
        """Release the underlying connection pool."""
        self._client.close()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed document passages, with no prefix."""
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            vectors.extend(self._embed_batch(texts[start : start + self._batch_size]))
        return vectors

    def embed_query(self, query: str) -> list[float]:
        """Embed a search query with the query prefix."""
        return self._embed_batch([f"{QUERY_PREFIX}{query}"])[0]

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Send one request and return vectors in input order.

        # #CRITICAL: Privacy: Errors carry status and counts only, never input text
        # #VERIFY: tests/unit/test_embedding_client.py checks error messages for leakage
        """
        if not texts:
            return []
        payload = {"model": self.model, "input": texts if len(texts) > 1 else texts[0]}
        try:
            response = self._client.post(EMBEDDINGS_PATH, json=payload)
        except httpx.HTTPError as exc:
            msg = f"Embedding request failed: {type(exc).__name__}"
            raise EmbeddingError(msg) from exc
        if response.status_code != httpx.codes.OK:
            msg = f"Embedding service returned HTTP {response.status_code}"
            raise EmbeddingError(msg)

        try:
            data = response.json()["data"]
            ordered = sorted(data, key=lambda item: item.get("index", 0))
            vectors = [[float(x) for x in item["embedding"]] for item in ordered]
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            msg = "Embedding service returned a malformed body"
            raise EmbeddingError(msg) from exc

        if len(vectors) != len(texts):
            msg = f"Embedding service returned {len(vectors)} vectors for {len(texts)} inputs"
            raise EmbeddingError(msg)
        if any(len(vector) != EXPECTED_DIMENSIONS for vector in vectors):
            msg = f"Embedding service returned vectors that are not {EXPECTED_DIMENSIONS} dimensions"
            raise EmbeddingError(msg)
        return vectors
