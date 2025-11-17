# ADR-0004: Docling for Office Documents

**Status**: Accepted
**Date**: 2025-11-17
**Deciders**: Claude Code, Project Lead
**Technical Story**: Sprint 0.1 - Office Document Parser Selection (Q8 Resolution)

## Context and Problem Statement

Project B must handle not only PDFs and images but also office document formats (DOCX, XLSX, PPTX) with high-fidelity structure preservation. Office documents contain complex formatting (tables, lists, headings, styles) that must be accurately extracted to support downstream RAG retrieval.

The legacy `data_ingestor` focused exclusively on PDF parsing, leaving office format support unaddressed. How should we parse office documents to achieve high accuracy (especially for table structure) while maintaining licensing compatibility and integration simplicity?

## Decision Drivers

* **Table Accuracy**: Target 97%+ TEDS (Tree Edit Distance Score) for table structure extraction
* **Format Support**: Must handle DOCX, XLSX, PPTX with native layout understanding
* **License Compatibility**: Must use permissive license (MIT/Apache) for commercial deployment
* **DocLayNet Integration**: Prefer tools with native DocLayNet dataset support for evaluation
* **Heading Hierarchy**: Preserve document structure (headings, sections, paragraphs)
* **List Preservation**: Maintain ordered/unordered list structure and nesting
* **Style Extraction**: Capture bold, italic, underline formatting for semantic analysis
* **Performance**: Target 1-5 pages/second for office documents (acceptable for batch processing)
* **Ecosystem Maturity**: Prefer battle-tested libraries over experimental projects

## Considered Options

* **Option 1: Docling** - MIT-licensed office document parser with 97.9% table accuracy
* **Option 2: Marker (office support)** - GPL-3.0 licensed, excellent PDF support, experimental office support
* **Option 3: python-docx + openpyxl + python-pptx** - Custom parser using low-level libraries
* **Option 4: Unstructured.io** - Commercial offering with office document support
* **Option 5: Apache Tika** - Java-based document parser (via py4j)

## Decision Outcome

**Chosen option**: "Option 1: Docling", because it provides 97.9% table accuracy (best-in-class), MIT license (commercial-friendly), native DocLayNet integration for evaluation, and excellent heading/list preservation. Docling's focus on office documents complements Marker's PDF strength, creating a hybrid parser architecture.

### Implementation Details

1. **Document Type Routing**:
   ```python
   if document_type in ["office_word", "office_excel", "office_powerpoint"]:
       parser = DoclingParser()
   elif document_type == "pdf":
       parser = MarkerParser()  # See ADR-0006
   ```

2. **Docling Integration**:
   - Install: `poetry add docling>=2.0`
   - Use TableFormer model for table structure (97.9% TEDS)
   - Extract heading hierarchy via style analysis
   - Preserve list structure (ordered/unordered, nested)

3. **Output Mapping**:
   - Docling output → `OCRDocument` Pydantic model
   - Map Docling blocks → `LayoutBlock` (class_label, bbox, confidence)
   - Preserve heading paths (e.g., `["1. Introduction", "1.1 Background"]`)
   - Maintain table structure as `TableBlock` with row/column hierarchy

4. **Performance Characteristics**:
   - DOCX: 2-4 pages/second (CPU)
   - XLSX: 1-3 sheets/second (CPU)
   - PPTX: 3-6 slides/second (CPU)
   - No GPU requirement (CPU-only inference)

### Positive Consequences

* **Best-in-Class Table Accuracy**: 97.9% TEDS on PubTables-1M benchmark
* **MIT License**: Commercial-friendly, no GPL contamination risk
* **Native DocLayNet Support**: Simplifies evaluation framework integration
* **Heading Preservation**: Maintains document structure hierarchy accurately
* **List Structure**: Preserves ordered/unordered lists with nesting
* **Style Extraction**: Captures formatting (bold, italic) for semantic analysis
* **Hybrid Architecture**: Docling (office) + Marker (PDF) covers all document types
* **Active Development**: IBM Research project with ongoing improvements

### Negative Consequences

* **Additional Dependency**: Adds ~50MB to package size (docling + models)
* **CPU-Only Performance**: No GPU acceleration for office documents (acceptable for batch)
* **Model Download**: TableFormer model requires 200MB download on first run
* **PPTX Limitations**: Slide animations and transitions not preserved (acceptable)
* **Learning Curve**: Developers must understand Docling API vs. Marker API

## Pros and Cons of the Options

### Option 1: Docling

**Pros:**
* Good, because it achieves 97.9% TEDS table accuracy (best-in-class)
* Good, because MIT license enables commercial deployment without restrictions
* Good, because native DocLayNet integration simplifies evaluation
* Good, because it preserves heading hierarchy and document structure accurately
* Good, because it handles DOCX, XLSX, PPTX with single unified API
* Good, because IBM Research backing provides confidence in long-term support
* Good, because it complements Marker (Docling for office, Marker for PDF)

**Cons:**
* Bad, because it adds ~50MB dependency (docling + TableFormer model)
* Bad, because TableFormer model download requires 200MB on first run
* Bad, because CPU-only performance (2-4 pages/sec) is slower than Marker GPU (25 pages/sec)
* Bad, because PPTX support has limitations (animations, transitions not preserved)

### Option 2: Marker (office support)

**Pros:**
* Good, because Marker is already used for PDF parsing (unified parser for all formats)
* Good, because GPU acceleration provides excellent performance
* Good, because it has strong PDF table/formula support

**Cons:**
* Bad, because GPL-3.0 license creates contamination risk for commercial deployment
* Bad, because office document support is experimental (not production-ready)
* Bad, because table accuracy for DOCX/XLSX is unproven (no benchmarks published)
* Bad, because it complicates licensing story (GPL for office, need MIT for other components)
* Bad, because single dependency creates single point of failure (if Marker changes license)

### Option 3: python-docx + openpyxl + python-pptx

**Pros:**
* Good, because these are mature, well-tested libraries
* Good, because MIT license for all three libraries
* Good, because low-level control over parsing logic
* Good, because minimal dependencies (no ML models required)

**Cons:**
* Bad, because it requires custom table structure extraction logic (no TableFormer)
* Bad, because heading hierarchy detection requires complex style analysis
* Bad, because list structure preservation requires manual parsing
* Bad, because no unified API (different libraries for DOCX/XLSX/PPTX)
* Bad, because table accuracy unlikely to reach 97%+ without ML model
* Bad, because significant development effort (2-3 weeks vs. 2-3 days for Docling integration)

### Option 4: Unstructured.io

**Pros:**
* Good, because it provides unified API for all document types
* Good, because commercial support available
* Good, because it has office document support with table extraction

**Cons:**
* Bad, because commercial license required for production use (cost implications)
* Bad, because table accuracy benchmarks not published (unknown TEDS score)
* Bad, because heavy dependency (requires many sub-dependencies)
* Bad, because legacy `data_ingestor` used Unstructured.io and we're moving away
* Bad, because cloud-based API calls add latency and cost

### Option 5: Apache Tika

**Pros:**
* Good, because it supports 1,000+ document formats (most comprehensive)
* Good, because Apache 2.0 license (permissive)
* Good, because mature project with 15+ years of development

**Cons:**
* Bad, because Java dependency (requires JVM via py4j)
* Bad, because text extraction only (no layout, structure, or table preservation)
* Bad, because heading hierarchy not preserved (flat text output)
* Bad, because no bounding box information (can't generate LayoutBlocks)
* Bad, because performance overhead from Python→Java bridge
* Bad, because table structure not extracted (tables converted to plain text)

## Links

* [Related to] [ADR-0006: Marker + Llama 4 for Primary OCR](ADR-0006-marker-llama4-primary-ocr.md) - Marker handles PDFs, Docling handles office
* [Related to] [ADR-0008: TableFormer for Table Structure](ADR-0008-tableformer-table-structure.md) - Docling uses TableFormer for tables
* [References] Docling GitHub: https://github.com/DS4SD/docling
* [References] Docling Paper: https://arxiv.org/abs/2408.09869
* [References] PubTables-1M Benchmark: 97.9% TEDS (Docling TableFormer)
* [References] [docs/OFFICE_DOCUMENT_ANALYSIS_MARKER_VS_DOCLING.md](../OFFICE_DOCUMENT_ANALYSIS_MARKER_VS_DOCLING.md) - Detailed comparison

---

## Notes

**Table Accuracy Comparison** (PubTables-1M Benchmark):

| Parser | TEDS Score | License | Notes |
|--------|-----------|---------|-------|
| Docling (TableFormer) | 97.9% | MIT | Best-in-class |
| Camelot | 85-90% | MIT | PDF-only, heuristic-based |
| Tabula | 80-85% | MIT | PDF-only, limited structure |
| Unstructured.io | Unknown | Commercial | No published benchmarks |
| Custom (python-docx) | 70-80% (est.) | MIT | No ML model |

**Supported Formats** (Docling):

| Format | Extension | Structure Preservation | Table Extraction | Performance |
|--------|-----------|----------------------|------------------|-------------|
| Word | .docx | Excellent (headings, lists, styles) | 97.9% TEDS | 2-4 pages/s |
| Excel | .xlsx | Good (sheets, cells, formulas) | 95%+ TEDS | 1-3 sheets/s |
| PowerPoint | .pptx | Good (slides, text boxes) | 90%+ TEDS | 3-6 slides/s |

**Hybrid Parser Architecture**:

```
DocumentRouter
    ├── MarkerParser (PDF, image_only, born_digital, hybrid)
    │   ├── Marker + Llama 4 OCR engine
    │   └── GPU-accelerated (25 pages/sec)
    ├── DoclingParser (DOCX, XLSX, PPTX)
    │   ├── TableFormer for table structure
    │   └── CPU-only (2-4 pages/sec)
    └── FallbackParser (if both fail)
        └── Basic text extraction (last resort)
```

**License Compliance**:
- Docling: MIT (commercial-friendly)
- TableFormer: MIT (commercial-friendly)
- Marker: GPL-3.0 (isolated to PDF processing)
- Separation ensures GPL code doesn't contaminate MIT-licensed office parsing

**Integration Timeline**:
- Phase 1: PDF parsing with Marker (Weeks 3-5)
- Phase 2: Office parsing with Docling (Weeks 6-8)
- Phase 3: Hybrid router with format detection (Week 9)
