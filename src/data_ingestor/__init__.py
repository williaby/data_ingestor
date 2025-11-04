"""
Data Ingestor - RAG Data Ingestion Pipeline.

A comprehensive data ingestion pipeline for RAG systems that transforms diverse
document formats (PDF, DOCX, websites, video) into high-quality, structured data
with optimal chunking and metadata preservation.
"""

__version__ = "0.1.0"
__author__ = "Byron Williams"
__email__ = "byronawilliams@gmail.com"

from data_ingestor.core.config import Settings
from data_ingestor.pipeline.router import DocumentRouter

__all__ = ["DocumentRouter", "Settings", "__version__"]
