# API Reference

Complete API documentation for Data Ingestor components.

## Core Modules

- **[Core Models](api/core.md)**: Document, Element, Metadata models
- **[Parsers](api/parsers.md)**: PDF, DOCX, HTML parsers
- **[Pipeline](api/pipeline.md)**: DocumentRouter, ParserRegistry
- **[Chunking](api/chunking.md)**: TokenChunker, ByTitleChunker
- **[Export](api/export.md)**: JSON and Markdown exporters
- **[Evaluation](api/evaluation.md)**: DocLayNet, PubTables evaluators
- **[Benchmarking](api/benchmarking.md)**: Orchestrator, Runner, Reporter

## Usage Examples

### Basic Document Processing

```python
from data_ingestor.pipeline.router import DocumentRouter
from data_ingestor.export.exporter import DocumentExporter

# Initialize router
router = DocumentRouter()

# Process document
document = router.process("document.pdf")

# Export to JSON
exporter = DocumentExporter()
exporter.export_json(document, "output.json")
```

### Advanced Chunking

```python
from data_ingestor.chunking.by_title_chunker import ByTitleChunker

# Section-aware chunking
chunker = ByTitleChunker(
    chunk_size=500,
    combine_under_n_chars=100
)

chunks = chunker.chunk(document)
```

## Auto-Generated API Docs

::: data_ingestor.core.models
    options:
      show_root_heading: true
      show_source: false

::: data_ingestor.pipeline.router
    options:
      show_root_heading: true
      show_source: false
