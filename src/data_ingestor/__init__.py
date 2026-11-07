"""
Data Ingestor - RAG Data Ingestion Pipeline.

A comprehensive data ingestion pipeline for RAG systems that transforms diverse
document formats (PDF, DOCX, websites, video) into high-quality, structured data
with optimal chunking and metadata preservation.

Pipeline stages currently implemented in this package:

* **Format detection** -- :mod:`data_ingestor.utils.format_detector`
* **File validation** -- :meth:`data_ingestor.core.base.BaseParser.validate_document`
* **PDF pre-flight (analysis + upscaling)** -- :mod:`data_ingestor.pipeline.pdf_analyzer`
* **PDF extraction** -- :mod:`data_ingestor.parsers.pdf_parser`
* **Chunking** -- :mod:`data_ingestor.chunking.token_chunker` and
  :mod:`data_ingestor.chunking.by_title_chunker`
* **Export / storage** -- :mod:`data_ingestor.export.exporter`
  (local filesystem only at present)
* **Orchestration** -- :class:`data_ingestor.pipeline.router.DocumentRouter`

Stages that appear in the wider RAG roadmap but are **not yet present**
in this package:

* Embedding stage (no embedding model wiring lives in this repo today;
  callers integrate with their own vector DB pipeline).
* Cloud storage backends (S3 / Azure / GCS) -- export currently writes
  to the local filesystem only.
"""

__version__ = "0.1.0"
__author__ = "Byron Williams"
__email__ = "byronawilliams@gmail.com"

from data_ingestor.core.config import Settings
from data_ingestor.pipeline.router import DocumentRouter

__all__ = ["DocumentRouter", "Settings", "__version__"]
