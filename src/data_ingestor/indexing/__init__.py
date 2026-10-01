"""Indexers that turn source material into Qdrant collections."""

from data_ingestor.indexing.tax_law import index_tax_law, load_knowledge_base

__all__ = ["index_tax_law", "load_knowledge_base"]
