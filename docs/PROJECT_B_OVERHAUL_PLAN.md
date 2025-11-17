# Project B Overhaul Plan: Layout, OCR & Structural Extraction Engine

**Version:** 1.0.0
**Date:** 2025-11-17
**Status:** DRAFT - Pending Approval
**Branch:** `claude/overhaul-data-ingestor-018ggaWu3fC5seyhuS7oGAPU`

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Context & Motivation](#2-context--motivation)
3. [Architecture Overview](#3-architecture-overview)
4. [Detailed Requirements](#4-detailed-requirements)
5. [Implementation Phases](#5-implementation-phases)
6. [Migration Strategy](#6-migration-strategy)
7. [Technical Specifications](#7-technical-specifications)
8. [Success Criteria](#8-success-criteria)
9. [Risk Management](#9-risk-management)
10. [Timeline & Resources](#10-timeline--resources)

---

## 1. Executive Summary

### 1.1 Current State

**data_ingestor** is a standalone document processing pipeline that:
- Ingests raw PDF/DOCX/HTML files directly
- Uses parser fallback chains (Marker → PyMuPDF4LLM → PyMuPDF)
- Performs chunking (token-based, by-title)
- Exports to JSON/Markdown
- Includes evaluation and benchmarking frameworks

### 1.2 Target State

**Project B** will become the **Layout, OCR & Structural Extraction Engine** in a 4-project RAG pipeline (A→B→C→D):
- **Consumes:** DocumentMetadata.json + corrected page images from Project A
- **Produces:** OCRDocument.json with layout blocks, reading order, and multi-engine OCR results for Project C
- **Core Capabilities:**
  - Layout detection (YOLOv8/v10, 11 DocLayNet classes)
  - Reading order prediction (graph-based algorithms)
  - OCR orchestration (Marker + DeepSeek-OCR, intelligent routing)
  - Specialized region detection (formulas, watermarks, stamps, signatures)
  - Logical structure assembly (shallow hierarchy, heading paths)

### 1.3 Scope of Change

- **Major Architectural Redesign:** ~60-70% of current code will be discarded or heavily refactored
- **New Core Capabilities:** Layout detection, reading order, multi-engine OCR orchestration
- **Removed Capabilities:** Direct file ingestion, chunking, markdown export
- **Estimated Effort:** 18 weeks for full implementation and handoff
- **New LOC:** ~4,700-6,800 lines of new/refactored code

---

## 2. Context & Motivation

### 2.1 The Four-Project Pipeline

```
┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
│          │      │          │      │          │      │          │
│ Project  │──────│ Project  │──────│ Project  │──────│ Project  │
│    A     │      │    B     │      │    C     │      │    D     │
│          │      │          │      │          │      │          │
│  Image   │      │ Layout,  │      │ Fusion,  │      │  Vector  │
│  Prep &  │      │   OCR &  │      │  Trust & │      │  DB &    │
│   IQA    │      │ Struct.  │      │ Chunking │      │ Retrieval│
│          │      │          │      │          │      │          │
└──────────┘      └──────────┘      └──────────┘      └──────────┘
     │                 │                 │                 │
     │                 │                 │                 │
     v                 v                 v                 v
Document          OCRDocument      FusedDocument       Embeddings
Metadata.json     .json            .json               + RAG
+ Images
```

### 2.2 Project B Mission Statement

> **"Determine WHERE content is, WHAT ORDER to read it, and WHAT IT SAYS—with sufficient structural detail that Project C can build trustworthy RAG chunks without re-guessing layout."**

### 2.3 Separation of Concerns

**What Project B DOES:**
- ✅ Detect layout elements (bounding boxes, classes)
- ✅ Predict reading order (sequential flow across complex layouts)
- ✅ Orchestrate OCR engines (route per region, store multi-engine results)
- ✅ Assemble logical structure (shallow hierarchy, heading paths)
- ✅ Detect specialized regions (formulas, watermarks, etc.)

**What Project B DOES NOT Do:**
- ❌ Image quality assessment / corrections (Project A)
- ❌ Multi-engine fusion / trust scoring (Project C)
- ❌ RAG chunking / noise filtering (Project C)
- ❌ Embeddings / vector storage (Project D)

### 2.4 Why Overhaul?

1. **Architectural Mismatch:** Current data_ingestor is a standalone tool; new Project B is a pipeline component
2. **Input Contract:** Must consume DocumentMetadata.json (not raw files)
3. **Output Contract:** Must produce OCRDocument.json (not custom Document model)
4. **New Capabilities:** Layout detection, reading order, multi-engine OCR not in current system
5. **Removed Capabilities:** Chunking, export, IQA moved to other projects
6. **Performance Requirements:** <300ms/page latency, 3-5 pages/sec throughput

---

## 3. Architecture Overview

### 3.1 Input Contract (from Project A)

```json
{
  "schema_version": "1.0.0",
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "source_path": "s3://bucket/documents/report.pdf",
  "document_type": "pdf",
  "pdf_type": "hybrid",
  "languages": ["en"],
  "page_count": 24,
  "pre_ocr_risk": 0.42,
  "dqs": {
    "degradation_score": 0.82,
    "structural_complexity_score": 0.65
  },
  "ocr_routing_recommendation": "ocr_advanced",
  "page_layout_summary": [
    {
      "page_index": 0,
      "layout_type": "multi_column",
      "has_tables": true,
      "has_figures": true,
      "has_dense_math": false,
      "has_handwriting": false,
      "page_attributes": {
        "fuzzy_scan": false,
        "watermark": true,
        "colorful_background": false
      }
    }
  ],
  "pages": [ ... ]
}
```

**Accompanying Artifacts:**
- Corrected page images (PNG/JPEG) at consistent DPI (300+)
- Storage: S3/GCS with paths in metadata
- Image corrections already applied (deskew, denoise, upscale)

### 3.2 Output Contract (to Project C)

```json
{
  "schema_version": "1.0.0",
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "page_count": 24,
  "layout_model_name": "yolov10_doc_doclaynet_v1",
  "ocr_engines": ["marker_llama4", "deepseek_ocr_v2"],
  "pages": [
    {
      "page_index": 0,
      "width_px": 2480,
      "height_px": 3508,
      "layout_blocks": [
        {
          "block_id": "p0_b001",
          "class_label": "text",
          "bbox": [120, 200, 1000, 150],
          "confidence": 0.95,
          "reading_order_index": 1
        },
        {
          "block_id": "p0_b002",
          "class_label": "table",
          "bbox": [120, 400, 1000, 600],
          "confidence": 0.92,
          "reading_order_index": 2
        }
      ],
      "reading_order": ["p0_b001", "p0_b002", "p0_b003"],
      "paragraphs": [
        {
          "paragraph_id": "p0_para001",
          "page_index": 0,
          "layout_block_id": "p0_b001",
          "heading_path": ["Chapter 1", "Introduction"],
          "structural_role": "body_text",
          "reading_order_index": 1,
          "ocr_engines": {
            "marker": {
              "text": "This is the introduction paragraph...",
              "confidence": 0.94
            },
            "deepseek_ocr": {
              "text": "This is the introduction paragraph...",
              "confidence": 0.92
            }
          },
          "languages": ["en"],
          "has_math": false,
          "has_table_ref": false,
          "has_handwriting": false
        }
      ]
    }
  ]
}
```

### 3.3 Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Project B Pipeline                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐                                            │
│  │   Input Parser   │  (DocumentMetadata.json → Pydantic model) │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           v                                                       │
│  ┌──────────────────┐                                            │
│  │ Layout Detector  │  (YOLOv8/v10-doc → COCO bboxes)           │
│  │   (GPU/CPU)      │                                            │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           v                                                       │
│  ┌──────────────────┐                                            │
│  │ Reading Order    │  (Spatial graph → ordered sequence)       │
│  │   Predictor      │                                            │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           v                                                       │
│  ┌──────────────────┐                                            │
│  │  OCR Engine      │  ┌─────────────┐  ┌─────────────┐        │
│  │  Orchestrator    │──│   Marker +  │  │ DeepSeek-   │        │
│  │                  │  │   Llama 4   │  │    OCR      │        │
│  └────────┬─────────┘  └─────────────┘  └─────────────┘        │
│           │                                                       │
│           v                                                       │
│  ┌──────────────────┐                                            │
│  │  Logical         │  (Hierarchy, heading paths, roles)        │
│  │  Structure       │                                            │
│  │  Assembler       │                                            │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           v                                                       │
│  ┌──────────────────┐                                            │
│  │ Specialized      │  (Formulas, watermarks, stamps, etc.)     │
│  │ Region Detector  │                                            │
│  └────────┬─────────┘                                            │
│           │                                                       │
│           v                                                       │
│  ┌──────────────────┐                                            │
│  │  Output          │  (OCRDocument.json → Pydantic → JSON)     │
│  │  Generator       │                                            │
│  └──────────────────┘                                            │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Detailed Requirements

### 4.1 Functional Requirements

#### FR-B1: Layout Detection

**Requirement:** Detect and classify document elements using deep object detection model.

**Model:** YOLOv8 or YOLOv10-doc trained on DocLayNet dataset

**Classes (11 DocLayNet Classes):**
1. Caption
2. Footnote
3. Formula
4. List-Item
5. Page-Footer
6. Page-Header
7. Picture
8. Section-Header
9. Table
10. Text
11. Title

**Output Format:** COCO bounding boxes `[x, y, width, height]` in pixels

**Post-Processing:**
- NMS (Non-Maximum Suppression) to eliminate overlapping boxes
- Low-confidence filtering (threshold: 0.5 default, configurable)
- Coordinate normalization and validation

**Accuracy Targets:**
- mAP@0.50: ≥ 0.82 (target), ≥ 0.75 (acceptable)
- mAP@0.50-0.95: ≥ 0.70
- Per-class AP: ≥ 0.75 for all 11 classes

**Performance Targets:**
- Latency: ≤ 100ms/page (GPU target), ≤ 300ms (acceptable)
- Throughput: ≥ 3-5 pages/sec per worker

#### FR-B2: Reading Order Prediction

**Requirement:** Determine sequential reading flow across complex, multi-column layouts.

**Approach:**
1. Construct spatial graph of layout elements
2. Assign edges based on adjacency (above/below, left/right, overlap)
3. Apply reading order algorithm:
   - Multi-column detection (2-3 columns)
   - Top-to-bottom per column, then next column
   - Title → Section-Header → body text progression
   - Table/caption, figure/caption placement
   - Footnotes after main text

**Output:**
- Per-page ordered sequence of block IDs
- Global reading_order_index per paragraph
- reading_order_confidence ∈ [0,1] (low confidence → signal to Project C for fallback)

**Accuracy Targets:**
- Pairwise F1: ≥ 0.85 (target)
- Kendall's tau: ≥ 0.80 (target)

**Validation Dataset:** ROOR / DocSynth reading order benchmarks

#### FR-B3: OCR Engine Orchestration

**Requirement:** Route regions to appropriate OCR engines, store multi-engine results.

**OCR Engines:**
- **Primary (Marker + Llama 4 Maverick):** Default for all regions
- **Secondary (DeepSeek-OCR):** For validation, complex regions, degraded pages

**Routing Logic:**
```python
def route_ocr_engine(block: LayoutBlock, metadata: DocumentMetadata) -> List[OCREngine]:
    engines = [MarkerEngine()]  # Always run Marker

    # Add DeepSeek-OCR if:
    if metadata.pre_ocr_risk > 0.6:  # High OCR risk
        engines.append(DeepSeekOCREngine())
    elif block.class_label in ["table", "formula"]:  # Complex structures
        engines.append(DeepSeekOCREngine())
    elif metadata.dqs.degradation_score < 0.5:  # Degraded pages
        engines.append(DeepSeekOCREngine())

    return engines
```

**Output:** Per-paragraph OCR results from all engines
```json
{
  "ocr_engines": {
    "marker": {"text": "...", "confidence": 0.94},
    "deepseek_ocr": {"text": "...", "confidence": 0.92}
  }
}
```

**Fallback Handling:**
- If DeepSeek-OCR unavailable → use Marker only, mark `ocr_engine_fallback = true`
- If Marker fails → attempt DeepSeek-OCR, log failure

**Accuracy Targets:**
- WER improvement: ≥ 10% relative vs Marker-only baseline
- CER improvement: ≥ 10% relative vs Marker-only baseline

#### FR-B4: Logical Structure Assembly

**Requirement:** Build shallow document hierarchy with heading paths and structural roles.

**Heading Path Tracking:**
```python
# Example: Track section hierarchy
heading_path = ["Chapter 1: Introduction", "Section 1.1 Background", "Subsection 1.1.1 Motivation"]
```

**Structural Roles:**
- body_text
- title
- section_header
- caption
- footnote
- table_context
- figure_context
- equation_context
- other

**Parent/Child Relationships:**
- Shallow hierarchy only (no deep nesting)
- Link captions to figures/tables (spatial proximity)
- Link footnotes to pages (position-based)

#### FR-B5: Specialized Region Detection

**Requirement:** Detect and flag specialized content regions.

**Priority Levels:**
- **P0 (Must Have):**
  - Formulas: Detect via layout model (Formula class)
- **P1 (Should Have):**
  - Watermarks: Detect via frequency domain analysis + layout hints
- **P2 (Nice to Have, Defer to v2):**
  - Stamps/Seals: Circle detection (Hough transform)
  - Signatures: Handwritten stroke detection
  - Margin Annotations: Edge isolation + handwriting detection

**Output:** Flags in specialized_content metadata
```json
{
  "specialized_content": {
    "has_formulas": true,
    "formula_count": 5,
    "has_watermarks": true,
    "watermark_regions": [{"bbox": [...], "confidence": 0.82}]
  }
}
```

### 4.2 Non-Functional Requirements

#### NFR-B1: Performance

**Latency Targets (GPU Mode):**
- Layout detection: < 100ms/page (target), < 300ms (acceptable)
- Reading order: < 50ms/page
- OCR (Marker): < 300ms/page (target), < 800ms (acceptable)
- OCR (DeepSeek): < 500ms/page (if invoked)
- Total pipeline: < 500ms/page (average), < 1200ms (p95)

**Throughput Targets:**
- > 3 pages/sec per worker (sustained, GPU)
- > 1 page/sec per worker (sustained, CPU fallback)

**Scaling:**
- Horizontal scaling via multiple workers
- Linear throughput scaling with worker count

#### NFR-B2: Robustness & Fallback

**Degradation Strategies:**
1. **Layout detection failure:**
   - Fallback: Simple page segmentation (horizontal stripes, column detection)
   - Mark: `layout_confidence = low` in output
2. **Reading order failure:**
   - Fallback: Top-to-bottom spatial ordering
   - Mark: `reading_order_confidence = low` in output
3. **OCR engine failure:**
   - Fallback: Use alternate engine or skip region
   - Mark: `ocr_engine_fallback = true` in output

**Error Handling:**
- Never fail entire document due to single-page error
- Partial results: Return successful pages, log failures
- Structured error logging with page context

#### NFR-B3: Logging & Observability

**Log Events (per page):**
- layout_detection_start
- layout_detection_complete (model, bbox count, latency)
- reading_order_complete (confidence, latency)
- ocr_engine_invoked (engine name, region count)
- ocr_complete (engine, latency, confidence)
- structure_assembly_complete
- page_processing_complete (total latency)

**Metrics Export (Prometheus-compatible):**
- `project_b_layout_latency_ms` (p50, p95, p99)
- `project_b_ocr_latency_ms` (per engine)
- `project_b_pages_processed_total`
- `project_b_errors_total` (by type)
- `project_b_layout_confidence_avg`
- `project_b_reading_order_confidence_avg`

**Debug Overlays (Optional):**
- Rendered page images with bboxes, labels, reading order indices
- Enabled via `--debug-overlays` flag
- Never logged at INFO level (privacy/security)

#### NFR-B4: Security & Privacy

- No external API calls except configured OCR/model services
- No page images or text in INFO-level logs (only hashed IDs)
- Debug overlays explicitly opt-in
- Container runs as non-root user
- Model files read-only access

---

## 5. Implementation Phases

### Phase 0: Foundation & Schema Definition (Weeks 1-2)

**Objectives:**
- Define Pydantic models for input/output schemas
- Set up new project structure
- Create test data and validation framework

**Deliverables:**
- ✅ `src/project_b/schemas/document_metadata.py` (Pydantic model)
- ✅ `src/project_b/schemas/ocr_document.py` (Pydantic model)
- ✅ JSON schema validation tests
- ✅ Sample test data (5-10 mock DocumentMetadata.json files)
- ✅ Project structure scaffold

**Success Criteria:**
- Schema validation passes for all test data
- Input/output round-trip successful

**Risks:**
- Schema interpretation ambiguity → Clarify with Project A team

---

### Phase 1: Layout Detection (Weeks 3-4)

**Objectives:**
- Integrate YOLOv8/v10-doc model
- Implement COCO bbox extraction and NMS
- Validate on DocLayNet dataset

**Deliverables:**
- ✅ `src/project_b/layout/detector.py` (YOLODetector class)
- ✅ `src/project_b/layout/postprocessing.py` (NMS, filtering)
- ✅ Model integration (ONNX or PyTorch)
- ✅ Unit tests (bbox extraction, NMS, class mapping)
- ✅ DocLayNet validation script
- ✅ Performance benchmarks (latency, mAP)

**Success Criteria:**
- mAP@0.50 ≥ 0.80 on DocLayNet validation (acceptable: ≥ 0.75)
- Latency ≤ 150ms/page on GPU (acceptable: ≤ 300ms)
- All 11 classes detected correctly

**Risks:**
- Model availability → Fallback: Train YOLOv8 on DocLayNet
- Performance on CPU → Optimization or GPU-only deployment

**Dependencies:**
- YOLOv8/v10-doc model (pre-trained or trained on DocLayNet)
- DocLayNet validation dataset

---

### Phase 2: Reading Order Prediction (Weeks 5-6)

**Objectives:**
- Implement spatial graph construction
- Implement graph-based reading order algorithms
- Validate on reading order benchmarks

**Deliverables:**
- ✅ `src/project_b/reading_order/graph.py` (SpatialGraph class)
- ✅ `src/project_b/reading_order/predictor.py` (ReadingOrderPredictor)
- ✅ Multi-column detection logic
- ✅ Reading order confidence scoring
- ✅ Unit tests (graph construction, ordering algorithms)
- ✅ Integration tests (end-to-end layout → reading order)
- ✅ Validation on ROOR/DocSynth datasets

**Success Criteria:**
- Pairwise F1 ≥ 0.82 on validation set (acceptable: ≥ 0.75)
- Kendall's tau ≥ 0.77 (acceptable: ≥ 0.70)
- Correct handling of multi-column layouts (verified on 100+ test cases)

**Risks:**
- Algorithm complexity → May require multiple iterations
- Edge cases (3-column, sidebars, callout boxes) → Progressive enhancement

**Dependencies:**
- Phase 1 complete (layout detection)
- Reading order validation dataset (ROOR/DocSynth or custom)

---

### Phase 3: OCR Orchestration (Weeks 7-9)

**Objectives:**
- Integrate Marker + Llama 4 Maverick
- Integrate DeepSeek-OCR (or fallback alternative)
- Implement routing logic and multi-engine output

**Deliverables:**
- ✅ `src/project_b/ocr/engines/marker.py` (MarkerEngine class)
- ✅ `src/project_b/ocr/engines/deepseek.py` (DeepSeekOCREngine class)
- ✅ `src/project_b/ocr/orchestrator.py` (OCROrchestrator with routing logic)
- ✅ Rate limiting and retry logic
- ✅ Fallback handling (engine unavailability)
- ✅ Unit tests (per-engine, routing logic)
- ✅ Integration tests (multi-engine OCR on test documents)
- ✅ WER/CER benchmarks vs single-engine baseline

**Success Criteria:**
- WER improvement ≥ 8% relative (target: ≥ 10%)
- OCR latency ≤ 400ms/page (Marker), ≤ 600ms (DeepSeek) on GPU
- Graceful fallback when DeepSeek unavailable

**Risks:**
- DeepSeek-OCR API access → Fallback: Tesseract + GPT-4o-mini
- API rate limits → Implement rate limiting and queuing
- Llama 4 Maverick integration → Use Marker's default LLM if unavailable

**Dependencies:**
- Marker library (existing)
- DeepSeek-OCR API access or alternative OCR engine
- Llama 4 Maverick model (optional enhancement)

---

### Phase 4: Logical Structure Assembly (Weeks 10-11)

**Objectives:**
- Implement paragraph aggregation
- Implement heading path tracking
- Implement structural role classification

**Deliverables:**
- ✅ `src/project_b/structure/assembler.py` (StructureAssembler class)
- ✅ Heading path extraction logic
- ✅ Structural role classifier
- ✅ Parent/child relationship builder
- ✅ Unit tests (heading extraction, role classification)
- ✅ Integration tests (full pipeline with structure)

**Success Criteria:**
- Heading paths extracted correctly (verified on 50+ test docs)
- Structural roles assigned correctly (> 90% accuracy on validation set)
- Shallow hierarchy built without errors

**Risks:**
- Heading detection ambiguity → Use font size + layout hints
- Complex hierarchies → Defer deep nesting to Project C

**Dependencies:**
- Phases 1-3 complete (layout, reading order, OCR)

---

### Phase 5: Specialized Regions (Weeks 12-13)

**Objectives:**
- Implement formula detection (P0)
- Implement watermark detection (P1)
- Defer stamps, signatures, margin annotations (P2, v2)

**Deliverables:**
- ✅ `src/project_b/specialized/formula_detector.py`
- ✅ `src/project_b/specialized/watermark_detector.py`
- ✅ Unit tests (detection accuracy)
- ✅ Integration tests (specialized regions in OCRDocument.json)

**Success Criteria:**
- Formula detection: Precision ≥ 0.90, Recall ≥ 0.85
- Watermark detection: Precision ≥ 0.85, Recall ≥ 0.80

**Risks:**
- Watermark detection complexity → Use simple heuristics + layout hints for v1

**Dependencies:**
- Phase 1 complete (layout detection)

---

### Phase 6: Integration & End-to-End Testing (Weeks 14-15)

**Objectives:**
- End-to-end pipeline testing
- Performance benchmarking
- Robustness testing (degraded inputs, fallback scenarios)

**Deliverables:**
- ✅ `src/project_b/pipeline/orchestrator.py` (Full pipeline)
- ✅ E2E integration tests (DocumentMetadata → OCRDocument)
- ✅ Performance benchmark suite (latency, throughput, resource usage)
- ✅ Stress tests (large documents, concurrent workers)
- ✅ Fallback scenario tests (engine failures, layout failures)
- ✅ DocLayNet + custom validation on full pipeline

**Success Criteria:**
- All E2E tests pass (> 95% success rate on validation set)
- Performance targets met (< 500ms/page avg, > 3 pages/sec)
- Fallback scenarios handled gracefully (no crashes)

**Risks:**
- Performance bottlenecks → Profiling and optimization
- Integration issues between phases → Refactoring may be needed

---

### Phase 7: Benchmarking & Evaluation Refactor (Weeks 16-17)

**Objectives:**
- Refactor existing benchmarking module to new schemas
- Generate baseline performance reports
- Compare against legacy data_ingestor (where applicable)

**Deliverables:**
- ✅ Refactored `src/project_b/benchmarking/` module
- ✅ Benchmark reports (HTML/JSON/CSV)
- ✅ Baseline metrics documented
- ✅ Comparison with legacy system (for migrated features)

**Success Criteria:**
- Benchmarking module adapted to OCRDocument.json schema
- Baseline reports generated for all key metrics
- Performance comparison shows improvement or parity

**Dependencies:**
- Phase 6 complete (full pipeline operational)

---

### Phase 8: Documentation & Handoff (Week 18)

**Objectives:**
- Update all project documentation
- Create deployment guides
- Handoff to Project C team

**Deliverables:**
- ✅ Updated `CLAUDE.md` with Project B architecture
- ✅ Updated `PROJECT_PLAN.md` (this document)
- ✅ API documentation (if REST API implemented)
- ✅ Deployment guide (Docker, Kubernetes, Modal)
- ✅ Troubleshooting guide (common errors, debugging)
- ✅ Handoff meeting with Project C team

**Success Criteria:**
- Documentation complete and reviewed
- Deployment guide validated on test environment
- Project C team trained on input/output schemas

---

## 6. Migration Strategy

### 6.1 Keep/Discard Decision Matrix

| Component | Decision | Rationale |
|-----------|----------|-----------|
| **KEEP** | | |
| `core/base.py` | Refactor | Base class patterns reusable, need new abstractions |
| `core/exceptions.py` | Keep + Extend | Error handling still needed |
| `core/config.py` | Refactor | Settings pattern reusable |
| `evaluation/` | Refactor | Metrics still relevant (mAP, WER, etc.) |
| `benchmarking/` | Refactor | Framework reusable, adapt to new schemas |
| `utils/rate_limiter.py` | Keep | Still needed for OCR API rate limiting |
| **DISCARD** | | |
| `chunking/` | Discard | Moved to Project C |
| `export/` | Discard | No markdown export needed |
| `parsers/pdf_parser.py` | Discard | Replaced by OCR orchestration |
| `pipeline/router.py` | Discard | Parser fallback logic not needed |
| `quality/` | Discard | Moved to Project A |
| `utils/format_detector.py` | Discard | Moved to Project A |
| `utils/pdf_upscaler.py` | Discard | Moved to Project A |
| `utils/pdf_resolution.py` | Discard | Moved to Project A |
| **NEW** | | |
| `layout/` | New | Layout detection (YOLOv8/v10) |
| `reading_order/` | New | Spatial graph, ordering algorithms |
| `ocr/` | New | Multi-engine orchestration |
| `structure/` | New | Hierarchy, heading paths |
| `specialized/` | New | Formulas, watermarks, etc. |
| `schemas/` | New | Pydantic models for input/output |

### 6.2 Migration Approach

**Option 1: Clean Slate (Recommended)**
- Create new `src/project_b/` directory
- Selectively copy reusable components from `src/data_ingestor/`
- Refactor and adapt as needed
- Keep legacy `src/data_ingestor/` for reference (tag as v1.0-legacy)

**Option 2: In-Place Refactor**
- Rename `src/data_ingestor/` to `src/project_b/`
- Delete discarded modules
- Refactor in-place
- Higher risk of merge conflicts, not recommended

**Decision:** Use Option 1 (Clean Slate)

### 6.3 Legacy Code Handling

- Tag current main branch as `v1.0-legacy`
- Preserve in separate branch: `legacy/data-ingestor-v1`
- Do NOT delete legacy code (may need reference during migration)
- Archive documentation in `docs/legacy/`

---

## 7. Technical Specifications

### 7.1 Technology Stack

**Core:**
- Python 3.11+ (type hints, Pydantic v2)
- Pydantic v2 (schema validation)
- PyTorch 2.0+ or ONNX Runtime (model inference)

**Layout Detection:**
- YOLOv8/v10 (ultralytics library or custom)
- OpenCV (bbox manipulation, NMS)

**Reading Order:**
- NetworkX (spatial graph construction)
- NumPy (spatial calculations)

**OCR Engines:**
- Marker (existing integration)
- Transformers (DeepSeek-OCR, Llama 4 Maverick)
- Alternative: Tesseract + OpenAI API

**Utilities:**
- Pillow (image I/O)
- structlog + rich (logging)
- prometheus-client (metrics export)

**Deployment:**
- Docker (containerization)
- FastAPI (REST API, optional)
- Kafka/RabbitMQ (message queue, optional)
- Modal (GPU burst capacity, optional)

### 7.2 Model Requirements

**YOLOv8/v10-doc:**
- Format: ONNX or PyTorch
- Input: RGB images (variable size, resized to 640x640 or 1280x1280)
- Output: COCO bboxes, class labels (11 DocLayNet classes), confidences
- Source: Pre-trained on DocLayNet or custom-trained

**Marker + Llama 4 Maverick:**
- Marker: PDF → Markdown with structure
- Llama 4 Maverick: Optional LLM enhancement (if available)
- Fallback: Use Marker's default LLM

**DeepSeek-OCR:**
- API-based or local inference
- Input: Cropped image regions
- Output: Text + confidence
- Fallback: Tesseract or OpenAI GPT-4o-mini

### 7.3 Deployment Models

**Option A: REST API**
```
POST /api/v1/process
{
  "document_metadata_path": "s3://bucket/metadata/doc123.json",
  "images_dir": "s3://bucket/images/doc123/"
}

Response:
{
  "ocr_document_path": "s3://bucket/ocr_documents/doc123.json",
  "status": "success",
  "processing_time_ms": 12450
}
```

**Option B: Message Queue Consumer**
```
Input Queue: project-a-output
Message: {document_id: ..., metadata_path: ..., images_dir: ...}

Processing: Project B consumes, processes, publishes

Output Queue: project-c-input
Message: {document_id: ..., ocr_document_path: ...}
```

**Option C: CLI (Dev/Testing Only)**
```bash
project-b process \
  --metadata /path/to/document_metadata.json \
  --images /path/to/images/ \
  --output /path/to/ocr_document.json
```

**Recommendation:** Message Queue (Kafka/RabbitMQ) for production, REST API for dev/testing

---

## 8. Success Criteria

### 8.1 Functional Success Criteria

- ✅ Consumes DocumentMetadata.json from Project A (schema-valid, 100% compliance)
- ✅ Produces OCRDocument.json for Project C (schema-valid, 100% compliance)
- ✅ Layout detection mAP@0.50 ≥ 0.82 on DocLayNet validation
- ✅ Reading order pairwise F1 ≥ 0.85 on ROOR/custom validation
- ✅ OCR WER improvement ≥ 10% relative vs Marker-only baseline
- ✅ All 11 DocLayNet classes detected with per-class AP ≥ 0.75
- ✅ Multi-column layouts handled correctly (verified on 100+ test cases)
- ✅ Tables, formulas, figures, footnotes handled correctly (verified on 100+ test cases)
- ✅ Specialized regions detected (formulas: P≥0.90, R≥0.85; watermarks: P≥0.85, R≥0.80)

### 8.2 Non-Functional Success Criteria

- ✅ Layout detection latency ≤ 100ms/page (GPU, target)
- ✅ OCR latency ≤ 300ms/page (GPU, target)
- ✅ Total pipeline latency < 500ms/page (average), < 1200ms (p95)
- ✅ Throughput ≥ 3 pages/sec per worker (sustained, GPU)
- ✅ Graceful degradation on failures (no document-level crashes)
- ✅ Comprehensive logging (per-page model usage, latency breakdowns)
- ✅ Prometheus metrics export functional
- ✅ Unit test coverage ≥ 80%
- ✅ Integration test coverage ≥ 70%
- ✅ E2E test success rate ≥ 95% on validation set

### 8.3 Documentation Success Criteria

- ✅ CLAUDE.md updated with Project B architecture
- ✅ PROJECT_PLAN.md (this document) complete
- ✅ API documentation published (if REST API)
- ✅ Deployment guide validated on test environment
- ✅ Troubleshooting guide covers common errors
- ✅ Project C team trained on schemas and handoff complete

---

## 9. Risk Management

### 9.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **YOLOv10-doc model unavailable** | Medium | High | Train YOLOv8 on DocLayNet as fallback |
| **DeepSeek-OCR API access denied** | Medium | Medium | Use Tesseract + GPT-4o-mini as fallback |
| **Reading order accuracy below target** | Medium | High | Iterative algorithm refinement, validation-driven |
| **Performance targets not met on CPU** | High | Medium | GPU-only deployment, batch optimization |
| **Llama 4 Maverick integration issues** | Low | Low | Use Marker's default LLM |
| **Schema interpretation ambiguity** | Low | Medium | Early coordination with Project A/C teams |

### 9.2 Organizational Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Project A delays** | Medium | High | Use mock data for development, validate later |
| **Project C requirements change** | Low | Medium | Schema versioning, backward compatibility |
| **Resource constraints (GPU)** | Medium | High | Modal GPU fallback, optimize for CPU where possible |
| **Timeline pressure** | Medium | Medium | Prioritize P0 features, defer P2 to v2 |

### 9.3 Dependency Risks

| Dependency | Risk | Mitigation |
|------------|------|------------|
| DocLayNet dataset | Licensing, availability | Mirror dataset locally, verify license |
| Marker library | API changes, bugs | Pin version, maintain fork if needed |
| DeepSeek-OCR | API reliability | Rate limiting, retry logic, fallback engine |
| Modal GPU | Cost, availability | Budget allocation, auto-scaling policies |

---

## 10. Timeline & Resources

### 10.1 Timeline Summary

```
Phase 0: Foundation           │██│ Weeks 1-2
Phase 1: Layout Detection     │████│ Weeks 3-4
Phase 2: Reading Order        │████│ Weeks 5-6
Phase 3: OCR Orchestration    │██████│ Weeks 7-9
Phase 4: Logical Structure    │████│ Weeks 10-11
Phase 5: Specialized Regions  │████│ Weeks 12-13
Phase 6: Integration & E2E    │████│ Weeks 14-15
Phase 7: Benchmarking         │████│ Weeks 16-17
Phase 8: Documentation        │██│ Week 18

Total Duration: 18 weeks (4.5 months)
```

### 10.2 Resource Requirements

**Engineering:**
- 1 Lead Engineer (full-time, all phases)
- 1 ML Engineer (Phases 1-3, 5: layout, OCR, specialized regions)
- 1 Backend Engineer (Phases 3-4, 6: OCR orchestration, integration)
- 0.5 QA Engineer (Phases 6-7: testing, validation)

**Infrastructure:**
- GPU workers: 2-4 T4/V100 GPUs for development + benchmarking
- CPU workers: 4-8 cores for fallback testing
- Storage: S3/GCS bucket for test data (~100GB)
- Modal GPU credits: ~$500-1000 for burst capacity

**External Dependencies:**
- YOLOv8/v10-doc model (pre-trained or training budget: ~$200-500)
- DeepSeek-OCR API access (TBD based on pricing)
- DocLayNet dataset (free, but need mirroring infra)
- ROOR/DocSynth reading order datasets (free)

### 10.3 Milestones

| Milestone | Week | Deliverable |
|-----------|------|-------------|
| **M1: Foundation Complete** | 2 | Schemas defined, test data created |
| **M2: Layout Detection Validated** | 4 | mAP ≥ 0.80 on DocLayNet |
| **M3: Reading Order Validated** | 6 | F1 ≥ 0.82 on validation set |
| **M4: OCR Orchestration Complete** | 9 | Multi-engine OCR, WER improvement ≥ 8% |
| **M5: Structure Assembly Complete** | 11 | Heading paths, roles working |
| **M6: Specialized Regions Complete** | 13 | Formulas, watermarks detected |
| **M7: E2E Pipeline Operational** | 15 | Full pipeline tested, performance targets met |
| **M8: Benchmarking Complete** | 17 | Baseline reports generated |
| **M9: Documentation & Handoff** | 18 | All docs updated, Project C handoff complete |

---

## 11. Open Questions & Next Steps

### 11.1 Open Questions (Need Decisions)

#### ✅ RESOLVED QUESTIONS

1. **Q1: YOLOv10-doc Availability** ✅ RESOLVED
   - ✅ **DECISION:** YOLOv10-doc is available
   - **Action:** Proceed with YOLOv10-doc integration in Phase 1
   - **Status:** APPROVED

2. **Q2: DeepSeek-OCR Access** ✅ RESOLVED
   - ✅ **DECISION:** Use Modal infrastructure for DeepSeek-OCR
   - **Implementation:** Unsloth option (https://docs.unsloth.ai/new/deepseek-ocr-how-to-run-and-fine-tune) for GPU optimization
   - **Infrastructure:** Project A has built out Modal infrastructure (reuse)
   - **Status:** APPROVED

3. **Q3: Llama 4 Maverick Integration** ✅ RESOLVED
   - ✅ **DECISION:** Llama 4 Maverick is available and tested with Marker
   - **Action:** Use Llama 4 Maverick for Marker integration in Phase 3
   - **Status:** APPROVED

4. **Q4: Table Structure Scope (v1 vs v2)** ✅ RESOLVED
   - ✅ **DECISION:** Table structure required for v1 (NOT deferred to v2)
   - **Action:** Implement table structure recognition (TableFormer or Table Transformer) in Phase 3
   - **Priority:** HIGH (Phase 3 deliverable)
   - **Status:** APPROVED

5. **Q5: Specialized Regions Priority** ✅ PARTIALLY RESOLVED
   - ✅ **DECISION (Implicit):** Based on table structure requirement, formulas are also P0
   - **Recommendation:**
     - P0: Formulas (layout detection + specialized OCR)
     - P0: Tables (structure recognition required for v1)
     - P1: Watermarks
     - P2: Stamps, Signatures, Margin Annotations (defer to v2)
   - **Status:** APPROVED (pending final confirmation)

6. **Q6: Storage for Page Images** ✅ RESOLVED
   - ✅ **DECISION:** GCS (Google Cloud Storage)
   - **Implementation:** Corrected page images stored in GCS, paths in DocumentMetadata.json
   - **Action:** Configure GCS client in Project B for image retrieval
   - **Status:** APPROVED

7. **Q7: Deployment Model (API vs Queue)** ⏳ PENDING
   - **Recommendation:** Message queue (Kafka) for production, REST API for dev/test
   - **Status:** Awaiting decision from Platform Team
   - **Deadline:** End of Week 3

#### ⏳ NEW QUESTIONS (Based on Office Document Analysis)

8. **Q8: Office Document Processing Approach** ⏳ PENDING
   - Marker (unified, GPL-3.0) vs Docling (specialized, MIT)?
   - **Recommendation:** Docling for office documents (see OFFICE_DOCUMENT_ANALYSIS_MARKER_VS_DOCLING.md)
   - **Status:** Awaiting approval
   - **Deadline:** End of Week 1

### 11.2 Next Steps (Immediate Actions)

**Week 1 Actions:**
1. ✅ Review and approve this Project B Overhaul Plan
2. ✅ Answer open questions Q1, Q4, Q5
3. ✅ Set up new branch: `project-b-overhaul` (already exists)
4. ✅ Create `src/project_b/` directory structure
5. ✅ Define Pydantic schemas for DocumentMetadata and OCRDocument
6. ✅ Create sample test data (5-10 mock DocumentMetadata.json files)
7. ✅ Coordinate with Project A team on schema alignment

**Week 2 Actions:**
1. ✅ Answer open questions Q2, Q6, Q7
2. ✅ Set up development environment (GPU workers, storage)
3. ✅ Source/train YOLOv8/v10-doc model
4. ✅ Set up DocLayNet validation dataset
5. ✅ Begin Phase 1: Layout Detection implementation
6. ✅ Schedule weekly sync with Project A/C teams

---

## Appendix A: Schema Definitions

### A.1 DocumentMetadata (Input from Project A)

See: `/docs/Ref Docs/RAG Pipeline/document_metadata.schema.json`

Key fields:
- `document_id`: UUID linking all pipeline stages
- `source_path`: S3/GCS path to original file
- `pdf_type`: image_only | born_digital | hybrid
- `dqs`: {degradation_score, structural_complexity_score}
- `ocr_routing_recommendation`: ocr_fast | ocr_advanced | vision_simple | vision_structured
- `page_layout_summary`: Coarse layout hints per page
- `pages`: Per-page IQA metrics, transform history

### A.2 OCRDocument (Output to Project C)

See: `/docs/Ref Docs/RAG Pipeline/ocr_document.schema.json`

Key fields:
- `document_id`: UUID matching DocumentMetadata
- `layout_model_name`: Identifier of layout model used
- `ocr_engines`: List of OCR engines used
- `pages[]`:
  - `layout_blocks[]`: {block_id, class_label, bbox, confidence, reading_order_index}
  - `reading_order[]`: Ordered list of block IDs
  - `paragraphs[]`: {paragraph_id, layout_block_id, heading_path, structural_role, ocr_engines{marker, deepseek_ocr}, ...}

---

## Appendix B: References

### B.1 Key Documents

- [RAG Pipeline Project Overview](/docs/Ref Docs/RAG Pipeline/RAG-pipeline-project-overview.md)
- [Project B Functional & Non-Functional Requirements](/docs/Ref Docs/RAG Pipeline/project-b-f-nf.md)
- [Project A F/NF Requirements](/docs/Ref Docs/RAG Pipeline/Project_A_F_NF.md)
- [Models Overview](/docs/Ref Docs/RAG Pipeline/MODELS.md)
- [Overhaul Analysis (Reference)](/home/user/data_ingestor/tmp_cleanup/.tmp-project-b-overhaul-analysis-20251117.md)

### B.2 Datasets & Benchmarks

- **DocLayNet:** https://github.com/DS4SD/DocLayNet
- **ROOR (Reading Order Benchmark):** https://github.com/google-research/google-research/tree/master/reading_order
- **PubTables-1M (Table Structure):** https://github.com/microsoft/table-transformer

### B.3 Models & Libraries

- **YOLOv10-doc:** https://github.com/ultralytics/ultralytics (DocLayNet-trained variant)
- **Marker + Llama 4 Maverick:** https://github.com/VikParuchuri/marker
- **DeepSeek-OCR (via Modal + Unsloth):** https://docs.unsloth.ai/new/deepseek-ocr-how-to-run-and-fine-tune
- **Transformers (Hugging Face):** https://github.com/huggingface/transformers
- **Docling (Office Documents):** https://github.com/docling-project/docling
- **TableFormer (Table Structure):** Part of Docling ecosystem

---

**Document Status:** DRAFT - Major questions resolved, ready for Phase 0 implementation

**Prepared By:** Claude Code (AI Assistant)
**Date:** 2025-11-17 (Updated: 2025-11-17 with resolved questions)
**Version:** 1.1.0
**Next Review:** End of Week 1 (2025-11-24)

**Resolved Questions:** 6/8 (Q1-Q6 approved, Q7-Q8 pending)
