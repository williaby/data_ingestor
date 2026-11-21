"""FastAPI application factory for the Data Ingestor REST API."""

from __future__ import annotations

from fastapi import FastAPI

from data_ingestor.api.routes import health, ingest, status
from data_ingestor.core.config import Settings

_SETTINGS = Settings()

API_DESCRIPTION = (
    "REST interface to the Data Ingestor pipeline. The pipeline transforms diverse "
    "document formats (PDF, DOCX, HTML, video, audio) into structured, chunked, and "
    "metadata-rich records suitable for retrieval-augmented generation. The API exposes "
    "three pipeline stages: ingest (submit a document and poll job status), health "
    "(process liveness and parser availability), and status (aggregate job and uptime "
    "metrics)."
)

OPENAPI_TAGS = [
    {"name": "ingest", "description": "Submit documents and poll per-job status."},
    {"name": "health", "description": "Liveness and parser-availability probes."},
    {"name": "status", "description": "Aggregate pipeline metrics."},
]


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application instance."""
    application = FastAPI(
        title="Data Ingestor API",
        description=API_DESCRIPTION,
        version=_SETTINGS.version,
        contact={
            "name": "Data Ingestor Maintainers",
            "url": "https://github.com/williaby/data_ingestor",
            "email": "byronawilliams@gmail.com",
        },
        license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
        openapi_tags=OPENAPI_TAGS,
    )

    application.include_router(ingest.router)
    application.include_router(health.router)
    application.include_router(status.router)

    return application


app = create_app()

__all__ = ["app", "create_app", "API_DESCRIPTION", "OPENAPI_TAGS"]
