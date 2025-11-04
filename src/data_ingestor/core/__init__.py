"""Core module containing base classes, interfaces, and configuration."""

from data_ingestor.core.base import BaseParser, Document, ParserResult
from data_ingestor.core.config import Settings
from data_ingestor.core.exceptions import (
    DataIngestorError,
    ParserError,
    UnsupportedFormatError,
)

__all__ = [
    "BaseParser",
    "DataIngestorError",
    "Document",
    "ParserError",
    "ParserResult",
    "Settings",
    "UnsupportedFormatError",
]
