# Project B Migration Guide

**Document Version**: 1.0.0
**Last Updated**: 2025-11-17
**Migration Status**: Phase 0 - Foundation & Planning

## Overview

This document outlines the migration strategy from the legacy `data_ingestor` implementation to the new **Project B** (Layout, OCR & Structural Extraction Engine) as part of the 4-project RAG pipeline architecture.

## Migration Strategy

**Approach**: Clean Slate Migration (Option 1)

We are creating a completely new implementation in `src/project_b/` while preserving the legacy codebase for reference. This approach was chosen because:

1. **Architectural Changes**: Project B has fundamentally different responsibilities (layout detection, OCR orchestration, structure assembly) vs. legacy data_ingestor (document parsing, chunking, export)
2. **Schema Changes**: New Pydantic v2 schemas (DocumentMetadata input, OCRDocument output) replace Unstructured.io-based models
3. **Technology Stack**: New core technologies (YOLOv10-doc, Marker+Llama4, Docling, TableFormer) require different integration patterns
4. **Clean Boundaries**: Separation of concerns across 4 projects requires clear interfaces and contracts

## Legacy Codebase Preservation

### Git Tag: `v1.0-legacy`

The legacy data_ingestor implementation has been preserved with tag `v1.0-legacy`:

```bash
# View the legacy implementation
git checkout v1.0-legacy

# Return to current development
git checkout claude/overhaul-data-ingestor-018ggaWu3fC5seyhuS7oGAPU
```

**Tagged Commit**: `b4fba4a` - "chore: add integration test structure and benchmark analysis utility"
**Completion Status**: Phase 1C complete (performance benchmarking baseline established)

### Reference Branch: `legacy/data-ingestor-v1`

A permanent reference branch has been created for historical reference:

```bash
# View legacy code
git checkout legacy/data-ingestor-v1

# Compare legacy vs new implementation
git diff legacy/data-ingestor-v1..HEAD src/

# Return to current development
git checkout claude/overhaul-data-ingestor-018ggaWu3fC5seyhuS7oGAPU
```

## Legacy Code Analysis

### What We're Keeping

The following components from the legacy codebase will be **refactored and adapted** for Project B:

1. **Evaluation Framework** (`src/data_ingestor/evaluation/`)
   - DocLayNet evaluator (layout + reading order metrics)
   - PubTables evaluator (table structure metrics)
   - Metric calculators (CER, BLEU, chrF, F1, mAP, TEDS)
   - **Adaptation**: Update for new schemas, add YOLOv10-doc evaluation

2. **Benchmarking Infrastructure** (`src/data_ingestor/benchmarking/`)
   - Orchestrator for multi-dataset parallel execution
   - Runner for dataset-specific processing
   - Reporter for HTML/JSON/CSV report generation
   - **Adaptation**: Update for layout/OCR benchmarks vs. end-to-end parsing

3. **Core Utilities** (`src/data_ingestor/utils/`)
   - Format detection (libmagic + mimetypes)
   - Logging infrastructure
   - Configuration management
   - **Adaptation**: Extend for GCS image retrieval, OCR engine coordination

### What We're Discarding

The following components are **no longer needed** in Project B and will be removed:

1. **Parser Infrastructure** (`src/data_ingestor/parsers/`)
   - PyMuPDF parsers (replaced by Marker + Docling)
   - Parser registry and fallback chains (moved to Project A preprocessing)
   - PDF page-by-page processing (handled by Marker)
   - **Reason**: Project B receives preprocessed images, not raw documents

2. **Chunking Logic** (`src/data_ingestor/chunking/`)
   - Token chunker, By-Title chunker
   - **Reason**: Chunking moved to Project C (Fusion & Chunking Engine)

3. **Export System** (`src/data_ingestor/export/`)
   - JSON/Markdown exporters
   - **Reason**: Project B outputs OCRDocument.json only (Project C handles final export)

4. **Quality Inspection** (`src/data_ingestor/quality/`)
   - Basic quality checks
   - **Reason**: Quality inspection moved to Project A (IQA & Preprocessing)

5. **CLI for Document Processing** (`src/data_ingestor/cli/main.py`)
   - `data-ingestor process` command
   - **Reason**: Project B has new CLI for layout/OCR pipeline (`project-b process`)

### Code Reuse Estimate

- **Keep with Refactoring**: ~30-40% (evaluation, benchmarking, utils)
- **Discard**: ~60-70% (parsers, chunking, export, quality)
- **New Code**: ~4,700-6,800 LOC (layout, reading order, OCR orchestration, structure assembly)

## New Project Structure

The new Project B implementation is located in `src/project_b/`:

```
src/project_b/
├── layout/              # YOLOv10-doc layout detection
├── reading_order/       # Spatial graph construction, multi-column handling
├── ocr/                 # OCR orchestration
│   └── engines/         # Marker, DeepSeek-OCR, Llama4
├── structure/           # Logical structure assembly (paragraphs, headings)
├── specialized/         # Table structure (TableFormer), formula detection
├── schemas/             # Pydantic v2 models (DocumentMetadata, OCRDocument)
├── pipeline/            # Main orchestration pipeline
├── cli/                 # Command-line interface (project-b)
├── utils/               # GCS integration, logging, config
└── tests/               # Comprehensive test suite (unit/integration/component/e2e)
```

## Migration Phases

### Phase 0: Foundation & Planning (Weeks 1-2) - **IN PROGRESS**

**Milestone 0.1: Project Structure Setup**
- ✅ Sprint 0.1.1: Create clean slate project structure (COMPLETED)
- 🔄 Sprint 0.1.2: Tag legacy code and create reference branch (IN PROGRESS)
- ⏳ Sprint 0.1.3: Set up development environment

**Milestone 0.2: Schema Definition**
- ⏳ Sprint 0.2.1: Define DocumentMetadata Pydantic model
- ⏳ Sprint 0.2.2: Define OCRDocument Pydantic model
- ⏳ Sprint 0.2.3: Create schema test suite

**Milestone 0.3: Test Data Generation**
- ⏳ Sprint 0.3.1: Create mock DocumentMetadata JSON files
- ⏳ Sprint 0.3.2: Create sample page images
- ⏳ Sprint 0.3.3: Create expected OCRDocument JSON outputs

### Phase 1: Layout Detection System (Weeks 3-5)

YOLOv10-doc integration, bounding box extraction, confidence scoring

### Phase 2: Reading Order Prediction (Weeks 6-7)

Spatial graph construction, multi-column handling, Kendall's tau evaluation

### Phase 3: OCR Orchestration Engine (Weeks 8-10)

Marker + Llama 4, DeepSeek-OCR fallback, multi-engine consensus

### Phase 4: Structural Analysis (Weeks 11-12)

Paragraph assembly, heading hierarchy, structural role classification

### Phase 5: Specialized Components (Weeks 13-14)

TableFormer integration, formula detection, image region handling

### Phase 6: Pipeline Integration (Week 15)

End-to-end orchestration, error handling, performance optimization

### Phase 7: Testing & Validation (Week 16)

DocLayNet evaluation, ROOR metrics, PubTables-1M table accuracy

### Phase 8: Documentation & Handoff (Weeks 17-18)

User guides, API documentation, deployment instructions

**Total Duration**: 18 weeks (~470 hours across 136 sprints)

## Testing Strategy

### Legacy Test Migration

1. **Evaluation Tests**: Migrate to new schemas, preserve metric calculations
2. **Benchmarking Tests**: Update for layout/OCR focus vs. end-to-end parsing
3. **Utility Tests**: Migrate directly with minimal changes
4. **Parser Tests**: Archive for reference, create new layout/OCR tests

### New Test Structure

```
src/project_b/tests/
├── unit/           # 60% - Isolated component testing
├── integration/    # 30% - Cross-component integration
├── component/      # Component-level with mocked dependencies
├── e2e/            # 10% - Full pipeline testing
└── fixtures/       # Shared test data
```

**Coverage Target**: 80%+ on `src/project_b/`

## Dependencies

### Legacy Dependencies (Removed)

- `unstructured` - Document parsing (replaced by Marker + Docling)
- `pymupdf` - PDF parsing (replaced by Marker)
- `tiktoken` - Chunking (moved to Project C)

### New Dependencies (Added)

- `ultralytics` (^8.0) - YOLOv10-doc layout detection
- `onnxruntime-gpu` (^1.16) - Optimized inference
- `marker-pdf` (^0.2) - Marker + Llama 4 OCR
- `transformers` (^4.35) - DeepSeek-OCR, Llama 4
- `docling` (^2.0) - Office document parsing (DOCX/XLSX/PPTX)
- `networkx` (^3.0) - Reading order graph construction
- `google-cloud-storage` (^2.10) - GCS image retrieval

### Preserved Dependencies

- `pydantic` (^2.0) - Schema validation
- `pytest` (^7.4) - Testing framework
- `black`, `ruff`, `mypy` - Code quality tools

## Rollback Plan

If critical issues arise during migration, we can rollback to the legacy implementation:

```bash
# Rollback to legacy implementation
git checkout v1.0-legacy

# Or create a new branch from legacy
git checkout -b rollback/legacy-restore v1.0-legacy
```

**Rollback Criteria**:
- Critical bugs in Project B blocking RAG pipeline
- Performance degradation >50% vs. legacy
- Unresolvable integration issues with Projects A/C/D

## Key Decisions

### Resolved Questions (9/9)

All critical architecture questions have been resolved:

1. ✅ **Q1**: YOLOv10-doc available and tested
2. ✅ **Q2**: DeepSeek-OCR via Modal infrastructure with Unsloth optimization
3. ✅ **Q3**: Llama 4 Maverick available and tested with Marker
4. ✅ **Q4**: Table structure required in v1 (not deferred)
5. ✅ **Q5**: Image storage via GCS (Google Cloud Storage)
6. ✅ **Q6**: Migration strategy: Clean Slate (Option 1) - **THIS DOCUMENT**
7. ✅ **Q7**: Deployment model: Hybrid (in-process primary, optional queue for batch)
8. ✅ **Q8**: Office documents: Docling (MIT license, 97.9% table accuracy)
9. ✅ **Q9**: Legacy preservation: Tag `v1.0-legacy` + branch `legacy/data-ingestor-v1` - **THIS DOCUMENT**

### Schema Contracts

**Input**: `DocumentMetadata.json` (from Project A)
- document_id, source_path, pdf_type
- dqs (degradation_score, structural_complexity_score)
- ocr_routing_recommendation
- page_layout_summary
- pages[] with corrected_image_gcs_path

**Output**: `OCRDocument.json` (to Project C)
- document_id, layout_model_name, ocr_engines
- pages[] with:
  - layout_blocks[] (bbox, class_label, confidence, reading_order_index)
  - reading_order[] (ordered block_ids)
  - paragraphs[] (heading_path, structural_role, multi-engine OCR results)

## Support and Resources

### Documentation

- **Project Plan**: `docs/PROJECT_B_OVERHAUL_PLAN.md` - Comprehensive 18-week implementation plan
- **Sprint Plan**: `docs/PROJECT_B_SPRINT_PLAN.md` - Detailed sprint breakdown (136 sprints)
- **Office Analysis**: `docs/OFFICE_DOCUMENT_ANALYSIS_MARKER_VS_DOCLING.md`
- **Deployment Model**: `docs/DEPLOYMENT_MODEL_ANALYSIS.md`
- **RAG Pipeline**: `docs/Ref Docs/RAG Pipeline/` - Full pipeline architecture

### Reference Schemas

- `docs/Ref Docs/RAG Pipeline/document_metadata.schema.json` - Input contract
- `docs/Ref Docs/RAG Pipeline/ocr_document.schema.json` - Output contract

### Legacy Codebase

- **Tag**: `v1.0-legacy` - Stable legacy implementation
- **Branch**: `legacy/data-ingestor-v1` - Permanent reference branch

---

**Migration Lead**: Claude Code
**Status**: Phase 0 in progress (Sprint 0.1.2)
**Next Milestone**: Milestone 0.2 - Schema Definition
