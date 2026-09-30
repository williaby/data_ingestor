"""FastAPI application: open GET /health and key-protected /api/v1 routes."""

import hmac
import logging

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from qdrant_client import QdrantClient

from data_ingestor.api.search import SearchRequest, SearchResponse, SearchService
from data_ingestor.core.config import Settings
from data_ingestor.core.exceptions import EmbeddingError
from data_ingestor.embedding import EmbeddingClient

logger = logging.getLogger(__name__)


def _error(status: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": detail})


def create_app(
    settings: Settings | None = None,
    embedder: EmbeddingClient | None = None,
    qdrant: QdrantClient | None = None,
) -> FastAPI:
    """Build the app. Service URLs and keys all come from settings.

    Raises:
        RuntimeError: If no service API key is configured
    """
    settings = settings or Settings()
    if settings.service_api_key is None or not settings.service_api_key.get_secret_value():
        msg = "DATA_INGESTOR_SERVICE_API_KEY must be set; refusing to start without an API key"
        raise RuntimeError(msg)
    expected_key = settings.service_api_key.get_secret_value().encode()

    if embedder is None:
        embed_key = settings.embed_api_key.get_secret_value() if settings.embed_api_key else ""
        embedder = EmbeddingClient(
            base_url=settings.embed_base_url,
            api_key=embed_key,
            model=settings.embedding_model,
            batch_size=settings.embed_batch_size,
            timeout=settings.embed_timeout,
        )
    if qdrant is None:
        qdrant_key = settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None
        qdrant = QdrantClient(url=settings.qdrant_url, api_key=qdrant_key)

    service = SearchService(
        client=qdrant,
        embedder=embedder,
        collections={"family-docs": settings.family_collection, "tax-law": settings.tax_law_collection},
        embedding_model=settings.embedding_model,
    )

    def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
        # Constant-time compare on bytes; a missing header is compared against nothing and rejected.
        supplied = (x_api_key or "").encode()
        if not x_api_key or not hmac.compare_digest(supplied, expected_key):
            raise HTTPException(status_code=401, detail="Invalid or missing API key")

    app = FastAPI(title="Data Ingestor", docs_url=None, redoc_url=None, openapi_url=None)
    router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_api_key)])

    @router.post("/search", response_model=SearchResponse)
    def search(request: SearchRequest) -> SearchResponse:
        return service.search(request)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_request: Request, _exc: RequestValidationError) -> JSONResponse:
        # The default handler echoes the rejected input back; this one does not.
        return _error(422, "Invalid request body")

    @app.exception_handler(EmbeddingError)
    async def _embedding_error(_request: Request, exc: EmbeddingError) -> JSONResponse:
        logger.error("Embedding service failure: %s", exc.message)
        return _error(502, "Embedding service unavailable")

    @app.exception_handler(Exception)
    async def _unhandled(_request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled error: %s", type(exc).__name__)  # type only; messages can carry text
        return _error(500, "Internal error")

    return app
