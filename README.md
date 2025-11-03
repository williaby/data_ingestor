# Data Ingestor - RAG Data Ingestion Pipeline

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive data ingestion pipeline for RAG (Retrieval-Augmented Generation) systems that transforms diverse document formats into high-quality, structured data with intelligent chunking and metadata preservation.

## Features

- **Multi-format Support**: PDF, DOCX, HTML, Video, Audio
- **Dual Output Formats**: Export as JSON, Markdown, or both with metadata preservation
- **Advanced Chunking Strategies**:
  - Token-based chunking with overlap
  - Section-aware chunking (by_title) that preserves document structure
- **Enhanced Element Types**: 15+ element types including formulas, code snippets, and hierarchical structures
- **Rich Metadata Model**: Coordinates, hierarchy tracking, emphasis preservation, and confidence scores
- **Parser Fallback Chains**: Automatic fallback to alternative parsers on failure
- **Format Detection**: Automatic document format detection using multiple strategies
- **Deduplication**: Hash-based duplicate detection
- **CLI Interface**: Easy-to-use command-line interface with extensive options
- **REST API**: FastAPI-based API endpoints (coming soon)

## Quick Start

### Installation

```bash
# Clone and install
git clone https://github.com/Byron/data_ingestor.git
cd data_ingestor

# Basic installation (PyMuPDF parsers)
poetry install

# With advanced PDF processing (Marker - requires GPU for best performance)
poetry install --with advanced-pdf

# For CPU-only systems (Marker will still work but slower)
poetry install --with advanced-pdf
# Then: export CUDA_VISIBLE_DEVICES=""  # Force CPU mode
```

**Note**: Marker provides the highest quality PDF extraction (especially for tables and formulas) but requires ~2GB of model downloads on first use. The system automatically falls back to PyMuPDF if Marker is not installed.

### Process a PDF Document

```bash
# Process a PDF and output to JSON
poetry run data-ingestor process document.pdf --output output.json

# Process and export as Markdown
poetry run data-ingestor process document.pdf --format markdown --output output.md

# Export both JSON and Markdown
poetry run data-ingestor process document.pdf --format both --output document

# Use section-aware chunking (preserves document structure)
poetry run data-ingestor process document.pdf --chunking-strategy by_title --output output.json

# Combine small sections (by_title only)
poetry run data-ingestor process document.pdf --chunking-strategy by_title --combine-under 500 --output output.json

# Check parser health
poetry run data-ingestor health
```

### Python API

```python
from data_ingestor.core.config import Settings
from data_ingestor.core.models import DocumentFormat
from data_ingestor.parsers.pdf_parser import PyMuPDFParser
from data_ingestor.pipeline.router import DocumentRouter
from data_ingestor.chunking import TokenChunker, ByTitleChunker, ChunkingStrategy
from data_ingestor.export import DocumentExporter, OutputFormat

# Initialize and process
settings = Settings()
router = DocumentRouter(settings)
router.parser_registry.register(PyMuPDFParser(), [DocumentFormat.PDF])

document, result = router.process_document(source_path="document.pdf")
print(f"Extracted {len(document.elements)} elements")

# Option 1: Token-based chunking (basic strategy)
token_chunker = TokenChunker(chunk_size=1000, chunk_overlap=200)
chunks = token_chunker.chunk_document(document)
print(f"Created {len(chunks)} chunks")

# Option 2: Section-aware chunking (by_title strategy)
section_chunker = ByTitleChunker(
    chunk_size=1000,
    chunk_overlap=200,
    combine_text_under_n_chars=500,  # Combine small sections
    respect_page_boundaries=False,    # Optional page boundary respect
)
chunks = section_chunker.chunk_document(document)
document.chunks = chunks

# Export in different formats
exporter = DocumentExporter()

# Export as JSON
json_data = exporter.to_json(document)

# Export as Markdown with YAML front matter
markdown = exporter.to_markdown(document, include_chunks=True)

# Export both formats
json_data, markdown = exporter.export(document, OutputFormat.BOTH)
```

## Architecture

- **Document Router**: Routes documents to appropriate parsers with fallback support
- **Parser Registry**: Manages multiple parsers per format with priority ordering
- **Format Detector**: Detects document format using libmagic and file extensions
- **Chunking Strategies**:
  - **Token Chunker**: Token-based segmentation with overlap
  - **By-Title Chunker**: Section-aware chunking that preserves document structure
- **Document Exporter**: Export to JSON, Markdown, or both with metadata preservation
- **Enhanced Element Types**: 15+ element types with rich metadata
- **Quality Assessor**: Validates extraction quality (coming soon)

### Element Types

The system supports 15+ element types based on Unstructured.io's taxonomy:

**Text Elements**: `TITLE`, `NARRATIVE_TEXT`, `LIST_ITEM`, `HEADER`, `FOOTER`

**Rich Content**: `TABLE`, `IMAGE`, `FIGURE_CAPTION`, `FORMULA`, `CODE_SNIPPET`

**Metadata Elements**: `ADDRESS`, `EMAIL_ADDRESS`, `PAGE_BREAK`, `PAGE_NUMBER`

**Special**: `COMPOSITE_ELEMENT` (chunking), `UNCATEGORIZED_TEXT`

### Enhanced Metadata

Each element includes comprehensive metadata:

- **Spatial**: Bounding box coordinates, page numbers
- **Hierarchy**: Parent-child relationships, category depth
- **Content**: HTML representations (tables), text emphasis tracking
- **Detection**: Model confidence scores
- **Custom**: User-defined regex extractions

### PDF Parser Comparison

The system uses a **fallback chain** strategy with three PDF parsers:

| Parser | Priority | Quality | Speed | Tables | Formulas | GPU | Installation |
|--------|----------|---------|-------|--------|----------|-----|--------------|
| **Marker** | Highest (10) | Excellent | Slow | ★★★★★ | ★★★★★ | Optional | `--with advanced-pdf` |
| **PyMuPDF4LLM** | Medium (100) | Very Good | Fast | ★★★ | ★★ | No | Default |
| **PyMuPDF** | Lowest (100) | Good | Very Fast | ★★ | ★ | No | Default |

**Automatic Fallback**: If Marker fails or isn't installed, the system automatically tries PyMuPDF4LLM, then PyMuPDF. This ensures reliability while maintaining quality when possible.

## Development Status

**Phase 1 (Current)**: Core foundation with PDF support

- [x] Core architecture and base classes
- [x] PDF parsing with PyMuPDF
- [x] **PDF parsing with Marker** (advanced tables/formulas)
- [x] Parser fallback chains
- [x] GPU detection and CPU fallback
- [x] Token-based chunking
- [x] **Section-aware chunking (by_title)**
- [x] **Dual output formats (JSON + Markdown)**
- [x] **Enhanced element types (15+ types)**
- [x] **Rich metadata model with hierarchy and coordinates**
- [x] CLI interface with extensive options
- [x] Format detection

**Phase 2 (Next)**: Multi-format expansion

- [ ] DOCX parsing
- [ ] Web scraping
- [ ] Video transcription
- [ ] Advanced PDF parser (Docling)
- [ ] REST API

See full [Project Plan](docs/project-plan.md) for details.

## License

MIT License - see [LICENSE](LICENSE) for details
