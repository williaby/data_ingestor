# Data Ingestor

**Production-grade RAG data ingestion pipeline for intelligent document processing**

---

## Overview

Data Ingestor is a comprehensive document processing system designed for RAG (Retrieval-Augmented Generation) applications. It provides:

- **Multi-format Support**: PDF, DOCX, HTML, and more
- **Intelligent Routing**: Automatic parser selection based on document characteristics
- **Advanced Parsers**: PyMuPDF, Marker (GPU-accelerated), Docling integration
- **Smart Chunking**: Section-aware and token-based strategies
- **Quality Metrics**: Comprehensive evaluation framework with DocLayNet
- **Production Ready**: 80%+ test coverage, security scanning, SBOM generation

## Key Features

### 🚀 **Intelligent Document Processing**
Adaptive OCR routing provides ~5x average speedup vs. blanket OCR through pre-flight analysis and intelligent routing.

### 📊 **Superior Table Accuracy**
97.9% table accuracy with Docling TableFormer integration for complex structured data extraction.

### 🔄 **Hybrid Parser Architecture**
- **Marker** (GPL-3.0): Advanced tables, formulas, intelligent OCR
- **PyMuPDF4LLM**: LLM-optimized markdown output
- **PyMuPDF**: Fast, reliable fallback
- **Docling** (MIT): Office formats (XLSX, PPTX, DOCX)

### 📏 **Evaluation Framework**
Comprehensive benchmarking with 81,471 DocLayNet documents:
- Layout mAP (mean Average Precision)
- Reading order F1 scores
- Table structure TEDS metrics
- Text accuracy (CER, BLEU, chrF)

## Quick Start

```bash
# Install with PyMuPDF parsers (basic)
poetry install

# Install with Marker for advanced PDF processing
poetry install --with advanced-pdf

# Process a document
poetry run data-ingestor process document.pdf --output output.json

# Run benchmarks
poetry run data-ingestor benchmark -d doclaynet -p pymupdf
```

## Project Status

**Current Phase**: Phase 1b - Performance Benchmarking & Baseline Establishment

See [Project Plan](PROJECT_PLAN.md) and [Completion Status](COMPLETION_STATUS.md) for detailed roadmap.

## Documentation

- **[Getting Started](getting-started/installation.md)**: Installation and quick start guide
- **[User Guide](guides/overview.md)**: Comprehensive usage documentation
- **[API Reference](api-reference.md)**: Detailed API documentation
- **[Architecture](architecture/design.md)**: System design and architecture
- **[Development](development/contributing.md)**: Contributing guidelines

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](project/license.md) file for details.

**Note**: The Marker parser (optional) uses GPL-3.0. See [Security Considerations](../CLAUDE.md#security-considerations) for details.
