"""Sources the Chunk stage reads documents from."""

from data_ingestor.core.exceptions import DocumentNotFoundError, DocumentSourceError
from data_ingestor.sources.documents_api import (
    TAX_RETURNS_CATEGORY,
    DocumentRecord,
    DocumentsApiClient,
    DownloadedFile,
)

__all__ = [
    "TAX_RETURNS_CATEGORY",
    "DocumentNotFoundError",
    "DocumentRecord",
    "DocumentSourceError",
    "DocumentsApiClient",
    "DownloadedFile",
]
