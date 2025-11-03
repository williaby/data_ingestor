# Data Ingestor - RAG Data Ingestion Pipeline

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive data ingestion pipeline for RAG (Retrieval-Augmented Generation) systems that transforms diverse document formats into high-quality, structured data with intelligent chunking and metadata preservation.

## Features

- **Multi-format Support**: PDF, DOCX, HTML, Video, Audio
- **Intelligent Chunking**: Token-based and element-based chunking strategies
- **Parser Fallback Chains**: Automatic fallback to alternative parsers on failure
- **Format Detection**: Automatic document format detection using multiple strategies
- **Deduplication**: Hash-based duplicate detection
- **CLI Interface**: Easy-to-use command-line interface
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

# Check parser health
poetry run data-ingestor health
```

### Python API

```python
from data_ingestor.core.config import Settings
from data_ingestor.core.models import DocumentFormat
from data_ingestor.parsers.pdf_parser import PyMuPDFParser
from data_ingestor.pipeline.router import DocumentRouter
from data_ingestor.chunking.token_chunker import TokenChunker

# Initialize and process
settings = Settings()
router = DocumentRouter(settings)
router.parser_registry.register(PyMuPDFParser(), [DocumentFormat.PDF])

document, result = router.process_document(source_path="document.pdf")
print(f"Extracted {len(document.elements)} elements")

# Chunk the document
chunker = TokenChunker(chunk_size=1000, chunk_overlap=200)
chunks = chunker.chunk_document(document)
print(f"Created {len(chunks)} chunks")
```

## Architecture

- **Document Router**: Routes documents to appropriate parsers with fallback support
- **Parser Registry**: Manages multiple parsers per format with priority ordering
- **Format Detector**: Detects document format using libmagic and file extensions
- **Token Chunker**: Intelligent document segmentation with overlap
- **Quality Assessor**: Validates extraction quality (coming soon)

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
- [x] CLI interface
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
