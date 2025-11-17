# Project B Sprint Plan: Detailed Milestone & Sprint Breakdown

**Date:** 2025-11-17
**Context:** Project B Overhaul - 18-Week Implementation Plan
**Sprint Duration:** 3-4 hours per sprint (single developer)
**Total Sprints:** ~150+ sprints across 8 phases

---

## Overview

This document breaks down the Project B Overhaul Plan into **Milestones** and **Sprints**:
- **Phase:** High-level stage of development (e.g., Phase 1: Layout Detection)
- **Milestone:** Measurable sub-goal within a phase (e.g., M1.1: YOLOv10 Integration)
- **Sprint:** Concrete 3-4 hour task for a single developer (e.g., S1.1.1: Set up ONNX Runtime)

---

## Phase 0: Foundation & Schema Definition (Weeks 1-2)

**Objective:** Define data models, set up project structure, create test data

### Milestone 0.1: Project Structure Setup (Week 1)

**Sprint 0.1.1:** Create Clean Slate Project Structure (3h)
- [ ] Create `src/project_b/` directory
- [ ] Set up Python package structure (`__init__.py` files)
- [ ] Create subdirectories: `layout/`, `reading_order/`, `ocr/`, `structure/`, `specialized/`, `schemas/`
- [ ] Set up `pyproject.toml` with dependencies
- [ ] Initialize pytest configuration

**Sprint 0.1.2:** Tag Legacy Code and Create Reference Branch (2h)
- [ ] Tag current main branch as `v1.0-legacy`
- [ ] Create `legacy/data-ingestor-v1` branch
- [ ] Archive legacy docs in `docs/legacy/`
- [ ] Update README with migration notice

**Sprint 0.1.3:** Set Up Development Environment (4h)
- [ ] Install YOLOv10-doc dependencies (ultralytics, ONNX Runtime)
- [ ] Install Docling for office documents
- [ ] Install Marker + Llama 4 Maverick dependencies
- [ ] Configure GCS client for image retrieval
- [ ] Set up Modal infrastructure connection (reuse Project A setup)

### Milestone 0.2: Schema Definition (Week 1-2)

**Sprint 0.2.1:** Define DocumentMetadata Pydantic Model (Input from Project A) (3h)
- [ ] Read `/docs/Ref Docs/RAG Pipeline/document_metadata.schema.json`
- [ ] Create `src/project_b/schemas/document_metadata.py`
- [ ] Define Pydantic models for:
  - DocumentMetadata
  - PageMetadata
  - DQS (Document Quality Score)
  - PageLayoutSummary
- [ ] Add JSON schema validation tests

**Sprint 0.2.2:** Define OCRDocument Pydantic Model (Output to Project C) (4h)
- [ ] Read `/docs/Ref Docs/RAG Pipeline/ocr_document.schema.json`
- [ ] Create `src/project_b/schemas/ocr_document.py`
- [ ] Define Pydantic models for:
  - OCRDocument
  - LayoutBlock
  - Paragraph
  - OCREngineResult
- [ ] Add JSON schema validation tests

**Sprint 0.2.3:** Create Schema Test Suite (3h)
- [ ] Write unit tests for DocumentMetadata parsing
- [ ] Write unit tests for OCRDocument serialization
- [ ] Create fixtures with sample JSON data
- [ ] Test round-trip (JSON → Pydantic → JSON)
- [ ] Validate against JSON schemas

### Milestone 0.3: Test Data Generation (Week 2)

**Sprint 0.3.1:** Create Mock DocumentMetadata JSON Files (3h)
- [ ] Create 5-10 mock DocumentMetadata.json files covering:
  - PDF (image_only, born_digital, hybrid)
  - Office documents (DOCX, XLSX, PPTX)
  - Various DQS scores (high/low degradation, simple/complex layout)
  - Single-page and multi-page documents
- [ ] Store in `tests/fixtures/document_metadata/`

**Sprint 0.3.2:** Create Sample Page Images (2h)
- [ ] Find or generate 10-20 sample page images (PNG/JPEG)
- [ ] Cover various layouts: single-column, multi-column, tables, formulas
- [ ] Upload to test GCS bucket or local storage
- [ ] Document image paths in mock DocumentMetadata files

**Sprint 0.3.3:** Create Expected OCRDocument JSON Outputs (4h)
- [ ] Manually create expected OCRDocument.json outputs for 3-5 test cases
- [ ] Include realistic layout_blocks[], reading_order[], paragraphs[]
- [ ] Cover edge cases: tables, formulas, multi-column, footnotes
- [ ] Store in `tests/fixtures/ocr_documents/`

---

## Phase 1: Layout Detection (Weeks 3-4)

**Objective:** Integrate YOLOv10-doc for 11 DocLayNet classes, validate on DocLayNet dataset

### Milestone 1.1: YOLOv10-doc Integration (Week 3)

**Sprint 1.1.1:** Set Up ONNX Runtime and Model Loading (3h)
- [ ] Install ONNX Runtime with GPU support
- [ ] Download YOLOv10-doc ONNX model (or convert from PyTorch)
- [ ] Create `src/project_b/layout/model_loader.py`
- [ ] Implement model loading with GPU/CPU fallback
- [ ] Write unit test (model loads successfully)

**Sprint 1.1.2:** Implement Image Preprocessing for YOLO (3h)
- [ ] Create `src/project_b/layout/preprocessor.py`
- [ ] Implement image resizing (640x640 or 1280x1280)
- [ ] Implement normalization (convert to RGB, normalize pixel values)
- [ ] Handle various input formats (PIL Image, NumPy array, file path)
- [ ] Write unit tests

**Sprint 1.1.3:** Implement YOLO Inference (4h)
- [ ] Create `src/project_b/layout/detector.py`
- [ ] Implement `LayoutDetector` class with `detect()` method
- [ ] Run YOLO inference on preprocessed image
- [ ] Parse YOLO output (bboxes, class labels, confidences)
- [ ] Write unit tests with sample image

**Sprint 1.1.4:** Map YOLO Classes to DocLayNet Classes (2h)
- [ ] Create `src/project_b/layout/class_mapper.py`
- [ ] Define mapping from YOLO class indices to DocLayNet class names
- [ ] Implement `map_class()` function
- [ ] Handle unknown classes (fallback to "unknown")
- [ ] Write unit tests

### Milestone 1.2: Post-Processing (Week 3)

**Sprint 1.2.1:** Implement Non-Maximum Suppression (NMS) (4h)
- [ ] Create `src/project_b/layout/postprocessing.py`
- [ ] Implement NMS algorithm (or use OpenCV/torchvision)
- [ ] Handle per-class NMS (don't suppress boxes of different classes)
- [ ] Add configurable IoU threshold (default: 0.4)
- [ ] Write unit tests with overlapping boxes

**Sprint 1.2.2:** Implement Low-Confidence Filtering (2h)
- [ ] Add confidence threshold parameter (default: 0.5)
- [ ] Filter out boxes with confidence < threshold
- [ ] Log number of boxes before/after filtering
- [ ] Write unit tests

**Sprint 1.2.3:** Implement COCO Bbox Format Conversion (3h)
- [ ] Convert YOLO bbox format (center_x, center_y, width, height)
- [ ] to COCO format [x, y, width, height] (top-left corner)
- [ ] Validate bboxes fit within page dimensions
- [ ] Clamp coordinates to page boundaries
- [ ] Write unit tests

**Sprint 1.2.4:** Implement Bbox Normalization and Validation (3h)
- [ ] Validate bbox coordinates are non-negative
- [ ] Validate width and height are positive
- [ ] Snap bboxes slightly inward (avoid adjacent column text)
- [ ] Round coordinates to integers
- [ ] Write unit tests with edge cases (out-of-bounds, zero-size)

### Milestone 1.3: Integration and Testing (Week 4)

**Sprint 1.3.1:** Create End-to-End Layout Detection Pipeline (4h)
- [ ] Create `src/project_b/layout/pipeline.py`
- [ ] Implement `LayoutPipeline` class
- [ ] Integrate: image loading → preprocessing → detection → post-processing
- [ ] Return list of LayoutBlock objects (Pydantic models)
- [ ] Write integration tests

**Sprint 1.3.2:** Add Per-Element Quality Hints (from Project A) (3h)
- [ ] Read per-element quality from DocumentMetadata.pages[].detected_elements[]
- [ ] Match Project A elements to Project B layout blocks (via bbox IoU)
- [ ] Attach quality_issues to LayoutBlock objects
- [ ] Write tests with mock DocumentMetadata

**Sprint 1.3.3:** Download DocLayNet Validation Dataset (2h)
- [ ] Download DocLayNet validation set (6,480 pages)
- [ ] Extract ground truth COCO annotations
- [ ] Store in `data/benchmarks/DocLayNet/`
- [ ] Create data loader script

**Sprint 1.3.4:** Implement Layout Detection Validation Script (4h)
- [ ] Create `scripts/validate_layout_detection.py`
- [ ] Load DocLayNet validation images + ground truth
- [ ] Run layout detection on all images
- [ ] Compute mAP@0.50, mAP@0.50-0.95, per-class AP
- [ ] Generate validation report (JSON, CSV)

**Sprint 1.3.5:** Run Validation and Analyze Results (3h)
- [ ] Run validation script on DocLayNet validation set
- [ ] Analyze mAP scores (target: mAP@0.50 ≥ 0.82)
- [ ] Identify low-performing classes (per-class AP < 0.75)
- [ ] Document results in `docs/validation_reports/phase1_layout.md`
- [ ] If results below target, plan iterations

**Sprint 1.3.6:** Performance Benchmarking (3h)
- [ ] Create `scripts/benchmark_layout_detection.py`
- [ ] Measure latency: per-page (p50, p95, p99)
- [ ] Measure throughput: pages/sec on GPU and CPU
- [ ] Test with various image sizes (640x640, 1280x1280, native resolution)
- [ ] Document results (target: ≤ 100ms/page GPU, ≤ 300ms acceptable)

---

## Phase 2: Reading Order Prediction (Weeks 5-6)

**Objective:** Implement spatial graph-based reading order algorithms, validate on ROOR/custom datasets

### Milestone 2.1: Spatial Graph Construction (Week 5)

**Sprint 2.1.1:** Implement Spatial Graph Data Structure (4h)
- [ ] Create `src/project_b/reading_order/graph.py`
- [ ] Define `SpatialGraph` class using NetworkX
- [ ] Nodes: LayoutBlock objects (from Phase 1)
- [ ] Edges: Adjacency relationships (above/below, left/right, overlap)
- [ ] Write unit tests

**Sprint 2.1.2:** Implement Adjacency Detection (Above/Below, Left/Right) (4h)
- [ ] Create `src/project_b/reading_order/adjacency.py`
- [ ] Implement `is_above()`, `is_below()`, `is_left_of()`, `is_right_of()` functions
- [ ] Use bbox geometric calculations
- [ ] Add tolerance parameters (allow small gaps/overlaps)
- [ ] Write unit tests with various bbox configurations

**Sprint 2.1.3:** Implement Overlap Detection (3h)
- [ ] Implement `compute_iou()` function (Intersection over Union)
- [ ] Implement `overlaps()` function (IoU > threshold)
- [ ] Add edge type: "overlaps" (for multi-column layouts)
- [ ] Write unit tests

**Sprint 2.1.4:** Build Spatial Graph from Layout Blocks (3h)
- [ ] Implement `build_graph()` function
- [ ] Iterate through layout blocks, add nodes
- [ ] Compute adjacency for all pairs, add edges
- [ ] Store edge features (distance, direction, overlap ratio)
- [ ] Write integration tests

### Milestone 2.2: Column Detection (Week 5)

**Sprint 2.2.1:** Implement Column Grouping Algorithm (4h)
- [ ] Create `src/project_b/reading_order/column_detector.py`
- [ ] Implement DBSCAN or X-coordinate clustering
- [ ] Detect 1-3 columns based on horizontal positions
- [ ] Assign `column_index` to each layout block
- [ ] Write unit tests with single-column, 2-column, 3-column layouts

**Sprint 2.2.2:** Detect Multi-Column Indicators (3h)
- [ ] Implement `is_multi_column()` function
- [ ] Heuristics: vertical spacing, horizontal gaps, bbox widths
- [ ] Set `is_multi_column` flag in spatial graph
- [ ] Write unit tests

### Milestone 2.3: Reading Order Algorithms (Week 5-6)

**Sprint 2.3.1:** Implement Single-Column Reading Order (3h)
- [ ] Create `src/project_b/reading_order/predictor.py`
- [ ] Implement `predict_single_column()` function
- [ ] Sort blocks top-to-bottom by Y-coordinate
- [ ] Handle ties (same Y) by sorting left-to-right
- [ ] Write unit tests

**Sprint 2.3.2:** Implement Multi-Column Reading Order (4h)
- [ ] Implement `predict_multi_column()` function
- [ ] Sort blocks by (column_index, Y-coordinate)
- [ ] Top-to-bottom within each column, then next column
- [ ] Handle column spanning elements (wide tables, titles)
- [ ] Write unit tests

**Sprint 2.3.3:** Handle Special Elements (Tables, Figures, Footnotes) (4h)
- [ ] Implement special handling for:
  - Tables: Keep before/after context
  - Captions: Place immediately after figure/table
  - Footnotes: Place at end of page
  - Headers/Footers: Mark as parasitic (exclude from reading order)
- [ ] Write unit tests

**Sprint 2.3.4:** Implement Reading Order Confidence Scoring (3h)
- [ ] Create `src/project_b/reading_order/confidence.py`
- [ ] Implement heuristics for confidence:
  - Clear column structure → high confidence
  - Complex overlaps → low confidence
  - Many ties in Y-coordinates → medium confidence
- [ ] Compute `reading_order_confidence` ∈ [0,1]
- [ ] Write unit tests

### Milestone 2.4: Cross-Page Coherence (Week 6)

**Sprint 2.4.1:** Implement Document-Level Reading Order (3h)
- [ ] Extend `ReadingOrderPredictor` to handle multi-page documents
- [ ] Assign global `reading_order_index` across all pages
- [ ] Maintain sequential numbering (page 1 blocks → page 2 blocks → ...)
- [ ] Write integration tests

**Sprint 2.4.2:** Handle Cross-Page Elements (Tables, Lists) (3h)
- [ ] Detect tables split across pages (heuristics: same bbox width, column headers)
- [ ] Detect lists split across pages (heuristics: list-item class, indentation)
- [ ] Mark split elements with `continues_from_previous_page` flag
- [ ] Write tests

### Milestone 2.5: Validation and Benchmarking (Week 6)

**Sprint 2.5.1:** Download Reading Order Validation Dataset (2h)
- [ ] Download ROOR benchmark or DocSynth reading order dataset
- [ ] Extract ground truth reading order annotations
- [ ] Store in `data/benchmarks/ReadingOrder/`
- [ ] Create data loader script

**Sprint 2.5.2:** Implement Reading Order Validation Metrics (4h)
- [ ] Create `scripts/validate_reading_order.py`
- [ ] Implement pairwise F1 metric (correct pairwise ordering)
- [ ] Implement Kendall's tau metric (order correlation)
- [ ] Run on validation dataset
- [ ] Generate validation report

**Sprint 2.5.3:** Run Validation and Analyze Results (3h)
- [ ] Run validation script
- [ ] Analyze F1 and Kendall's tau (target: F1 ≥ 0.85, tau ≥ 0.80)
- [ ] Identify failure modes (complex layouts, multi-column errors)
- [ ] Document results in `docs/validation_reports/phase2_reading_order.md`
- [ ] If results below target, plan iterations

**Sprint 2.5.4:** Performance Benchmarking (2h)
- [ ] Measure reading order prediction latency (target: < 50ms/page)
- [ ] Test on various layout complexities (simple, multi-column, complex)
- [ ] Document results

---

## Phase 3: OCR Orchestration (Weeks 7-9)

**Objective:** Integrate Marker + Llama 4 + DeepSeek-OCR, implement routing logic, validate WER/CER

### Milestone 3.1: Marker Integration (Week 7)

**Sprint 3.1.1:** Set Up Marker + Llama 4 Maverick (4h)
- [ ] Install Marker library with Llama 4 backend
- [ ] Configure Llama 4 Maverick model path
- [ ] Test basic PDF → Markdown conversion
- [ ] Document configuration in `docs/setup/marker_llama4.md`

**Sprint 3.1.2:** Create Marker Engine Wrapper (3h)
- [ ] Create `src/project_b/ocr/engines/marker.py`
- [ ] Implement `MarkerEngine` class with `ocr()` method
- [ ] Input: Image or PDF page
- [ ] Output: Text + confidence + metadata
- [ ] Write unit tests

**Sprint 3.1.3:** Implement Per-Region OCR for Marker (4h)
- [ ] Modify `MarkerEngine` to accept region bboxes
- [ ] Crop image to bbox before OCR
- [ ] Run Marker on cropped region
- [ ] Return per-region OCR results
- [ ] Write integration tests

**Sprint 3.1.4:** Extract Paragraph Structure from Marker (4h)
- [ ] Parse Marker's Markdown output to extract paragraphs
- [ ] Map Markdown headings to `heading_path`
- [ ] Map Markdown elements to `structural_role` (title, section_header, body_text, etc.)
- [ ] Write parser for Marker → Paragraph objects
- [ ] Write unit tests

### Milestone 3.2: DeepSeek-OCR Integration (Week 7-8)

**Sprint 3.2.1:** Set Up Modal Infrastructure for DeepSeek-OCR (3h)
- [ ] Review Project A's Modal setup (reuse configuration)
- [ ] Install Modal SDK
- [ ] Create Modal function stub for DeepSeek-OCR
- [ ] Test Modal connection (health check)

**Sprint 3.2.2:** Implement Unsloth-Optimized DeepSeek-OCR (4h)
- [ ] Follow https://docs.unsloth.ai/new/deepseek-ocr-how-to-run-and-fine-tune
- [ ] Implement GPU-optimized DeepSeek-OCR inference
- [ ] Deploy to Modal (or run locally if GPU available)
- [ ] Test on sample images
- [ ] Document setup in `docs/setup/deepseek_unsloth.md`

**Sprint 3.2.3:** Create DeepSeek-OCR Engine Wrapper (3h)
- [ ] Create `src/project_b/ocr/engines/deepseek.py`
- [ ] Implement `DeepSeekOCREngine` class with `ocr()` method
- [ ] Handle Modal API calls (or local inference)
- [ ] Implement retry logic (exponential backoff)
- [ ] Write unit tests (mock Modal responses)

**Sprint 3.2.4:** Implement Rate Limiting for DeepSeek-OCR (3h)
- [ ] Reuse `src/data_ingestor/utils/rate_limiter.py` (from legacy)
- [ ] Configure rate limits (e.g., 10 requests/second)
- [ ] Implement request queuing
- [ ] Add timeout handling
- [ ] Write unit tests

### Milestone 3.3: OCR Routing Logic (Week 8)

**Sprint 3.3.1:** Implement OCR Engine Router (4h)
- [ ] Create `src/project_b/ocr/router.py`
- [ ] Implement `route_engine()` function
- [ ] Routing logic based on:
  - DocumentMetadata (pre_ocr_risk, dqs, routing_recommendation)
  - LayoutBlock (class_label, quality_issues)
- [ ] Return list of engines to use (Marker, DeepSeek-OCR, or both)
- [ ] Write unit tests with various routing scenarios

**Sprint 3.3.2:** Implement Multi-Engine Orchestration (4h)
- [ ] Create `src/project_b/ocr/orchestrator.py`
- [ ] Implement `OCROrchestrator` class
- [ ] For each layout block:
  - Route to appropriate engines
  - Run OCR with each engine
  - Collect results
- [ ] Return per-paragraph multi-engine OCR results
- [ ] Write integration tests

**Sprint 3.3.3:** Implement Fallback Handling (3h)
- [ ] If DeepSeek-OCR unavailable → use Marker only
- [ ] If Marker fails → try DeepSeek-OCR
- [ ] Mark `ocr_engine_fallback = true` in metadata
- [ ] Log all fallback events
- [ ] Write tests for failure scenarios

### Milestone 3.4: Table Structure Recognition (Week 8-9)

**Sprint 3.4.1:** Research Table Structure Options (2h)
- [ ] Evaluate TableFormer (Docling ecosystem)
- [ ] Evaluate Table Transformer (Microsoft)
- [ ] Compare accuracy, speed, ease of integration
- [ ] Document decision in `docs/decisions/table_structure.md`

**Sprint 3.4.2:** Integrate TableFormer or Table Transformer (4h)
- [ ] Install chosen library
- [ ] Create `src/project_b/ocr/table_recognizer.py`
- [ ] Implement `TableRecognizer` class
- [ ] Input: Cropped table image
- [ ] Output: Row/column structure, cell contents
- [ ] Write unit tests

**Sprint 3.4.3:** Integrate Table Recognition into OCR Pipeline (3h)
- [ ] Detect table regions (class_label == "table")
- [ ] Run TableRecognizer on table crops
- [ ] Extract cell-level text with OCR
- [ ] Store table structure in Paragraph metadata
- [ ] Write integration tests

**Sprint 3.4.4:** Validate Table Structure Accuracy (3h)
- [ ] Download PubTables-1M validation subset
- [ ] Run table recognition on validation images
- [ ] Compute TEDS metric (target: ≥ 0.90)
- [ ] Document results in `docs/validation_reports/phase3_tables.md`

### Milestone 3.5: Validation and Benchmarking (Week 9)

**Sprint 3.5.1:** Create OCR Validation Dataset (3h)
- [ ] Collect or generate ground truth OCR text for 50-100 pages
- [ ] Cover various document types (clean, degraded, complex layouts)
- [ ] Store ground truth in `data/benchmarks/OCR/`

**Sprint 3.5.2:** Implement WER/CER Metrics (3h)
- [ ] Create `scripts/validate_ocr.py`
- [ ] Implement Word Error Rate (WER) calculation
- [ ] Implement Character Error Rate (CER) calculation
- [ ] Run on validation dataset
- [ ] Generate validation report

**Sprint 3.5.3:** Run OCR Validation and Analyze Results (4h)
- [ ] Run validation script
- [ ] Compute WER/CER for:
  - Marker only
  - DeepSeek-OCR only
  - Multi-engine (best result from each)
- [ ] Verify improvement ≥ 10% relative (target)
- [ ] Document results in `docs/validation_reports/phase3_ocr.md`

**Sprint 3.5.4:** Performance Benchmarking (3h)
- [ ] Measure OCR latency per page (Marker, DeepSeek-OCR, combined)
- [ ] Target: Marker ≤ 300ms, DeepSeek ≤ 500ms (GPU)
- [ ] Measure throughput (pages/sec)
- [ ] Document results

---

## Phase 4: Logical Structure Assembly (Weeks 10-11)

**Objective:** Implement heading path tracking, structural role classification, shallow hierarchy

### Milestone 4.1: Heading Path Extraction (Week 10)

**Sprint 4.1.1:** Implement Heading Detection (3h)
- [ ] Create `src/project_b/structure/heading_detector.py`
- [ ] Detect headings from layout blocks (class_label == "title" or "section_header")
- [ ] Extract heading text from OCR results
- [ ] Assign heading level (1-6) based on font size or position
- [ ] Write unit tests

**Sprint 4.1.2:** Implement Hierarchical Heading Path Tracking (4h)
- [ ] Create `src/project_b/structure/hierarchy_builder.py`
- [ ] Build heading hierarchy (nested list structure)
- [ ] Example: ["Chapter 1", "Section 1.1", "Subsection 1.1.1"]
- [ ] Assign heading_path to each paragraph based on context
- [ ] Write unit tests

**Sprint 4.1.3:** Handle Edge Cases (Skipped Levels, Multiple Headings) (3h)
- [ ] Handle skipped heading levels (e.g., H1 → H3, skip H2)
- [ ] Handle multiple headings on same page
- [ ] Handle headings without text (use bbox position as fallback)
- [ ] Write tests for edge cases

### Milestone 4.2: Structural Role Classification (Week 10)

**Sprint 4.2.1:** Implement Structural Role Classifier (4h)
- [ ] Create `src/project_b/structure/role_classifier.py`
- [ ] Map layout block class_label to structural_role:
  - title → title
  - section_header → section_header
  - text → body_text
  - caption → caption
  - footnote → footnote
  - table → table_context
  - picture → figure_context
  - formula → equation_context
- [ ] Write unit tests

**Sprint 4.2.2:** Implement Heuristic Refinements (3h)
- [ ] Refine structural roles based on:
  - Position (e.g., first text block after title → likely intro)
  - Length (e.g., short text blocks after figure → likely caption)
  - Context (e.g., text inside table → table_context)
- [ ] Write tests

### Milestone 4.3: Shallow Hierarchy Construction (Week 11)

**Sprint 4.3.1:** Implement Parent/Child Relationships (4h)
- [ ] Create `src/project_b/structure/assembler.py`
- [ ] Implement `StructureAssembler` class
- [ ] Assign parent_id to each layout block based on:
  - Headings → children are text blocks until next heading
  - Tables → children are captions (spatial proximity)
  - Figures → children are captions
- [ ] Write unit tests

**Sprint 4.3.2:** Implement Caption-to-Figure/Table Linking (3h)
- [ ] Use spatial proximity hints from Phase 1 (layout detection)
- [ ] Link caption to nearest figure/table (within threshold distance)
- [ ] Store link in `parent_id` or `related_elements` metadata
- [ ] Write tests

**Sprint 4.3.3:** Implement Footnote Linking (3h)
- [ ] Detect footnote regions (class_label == "footnote")
- [ ] Store footnote metadata (position at page bottom, estimated count)
- [ ] Do NOT implement reference linking (that's Project C's job)
- [ ] Write tests

### Milestone 4.4: Integration and Testing (Week 11)

**Sprint 4.4.1:** Integrate Structure Assembly into Pipeline (3h)
- [ ] Add `StructureAssembler` to OCR pipeline
- [ ] Input: LayoutBlocks + OCR results
- [ ] Output: Paragraphs with heading_path, structural_role, parent_id
- [ ] Write integration tests

**Sprint 4.4.2:** Create End-to-End Structure Validation (4h)
- [ ] Create validation script for structure assembly
- [ ] Manually verify heading paths on 10-20 test documents
- [ ] Check structural role accuracy (> 90% target)
- [ ] Document results in `docs/validation_reports/phase4_structure.md`

---

## Phase 5: Specialized Regions (Weeks 12-13)

**Objective:** Implement formula detection, watermark detection (defer stamps/signatures/margins to v2)

### Milestone 5.1: Formula Detection (Week 12)

**Sprint 5.1.1:** Implement Formula Region Detection (3h)
- [ ] Create `src/project_b/specialized/formula_detector.py`
- [ ] Use layout detection (class_label == "formula")
- [ ] Provide bounding boxes for formula regions
- [ ] Write unit tests

**Sprint 5.1.2:** Research Math OCR Options (Nougat, pix2tex) (2h)
- [ ] Evaluate Nougat (Meta)
- [ ] Evaluate pix2tex
- [ ] Compare accuracy, speed, licensing
- [ ] Document decision in `docs/decisions/math_ocr.md`

**Sprint 5.1.3:** Integrate Math OCR (Optional for v1) (4h)
- [ ] Install chosen math OCR library
- [ ] Create `src/project_b/specialized/math_ocr.py`
- [ ] Implement `MathOCR` class
- [ ] Input: Cropped formula image
- [ ] Output: LaTeX string
- [ ] Write unit tests

**Sprint 5.1.4:** Route Formula Regions to Math OCR (3h)
- [ ] Detect formula regions in OCR orchestrator
- [ ] Route to MathOCR if available
- [ ] Store LaTeX in Paragraph metadata (`has_math = true`, `math_latex` field)
- [ ] Write integration tests

**Sprint 5.1.5:** Validate Formula Detection Accuracy (3h)
- [ ] Create validation dataset (documents with formulas)
- [ ] Measure formula detection precision/recall (target: P ≥ 0.90, R ≥ 0.85)
- [ ] Document results in `docs/validation_reports/phase5_formulas.md`

### Milestone 5.2: Watermark Detection (Week 12-13)

**Sprint 5.2.1:** Implement Frequency Domain Watermark Detection (4h)
- [ ] Create `src/project_b/specialized/watermark_detector.py`
- [ ] Implement FFT-based watermark detection
- [ ] Detect repeating patterns (logos, text overlays)
- [ ] Output: Watermark presence flag + bounding boxes (if detectable)
- [ ] Write unit tests

**Sprint 5.2.2:** Implement Heuristic Watermark Detection (3h)
- [ ] Detect semi-transparent text overlays
- [ ] Detect diagonal text (common in watermarks)
- [ ] Detect repeated logos (template matching)
- [ ] Combine heuristics with frequency domain results
- [ ] Write tests

**Sprint 5.2.3:** Integrate Watermark Detection into Pipeline (3h)
- [ ] Add watermark detection to specialized region processing
- [ ] Mark detected watermarks with `is_parasitic = true`
- [ ] Store in `specialized_content` metadata
- [ ] Write integration tests

**Sprint 5.2.4:** Validate Watermark Detection Accuracy (3h)
- [ ] Create validation dataset (documents with/without watermarks)
- [ ] Measure precision/recall (target: P ≥ 0.85, R ≥ 0.80)
- [ ] Document results in `docs/validation_reports/phase5_watermarks.md`

### Milestone 5.3: Defer P2 Specialized Regions to v2 (Week 13)

**Sprint 5.3.1:** Document P2 Deferral (2h)
- [ ] Document deferred features in `docs/roadmap/v2_features.md`:
  - Stamps/Seals detection
  - Signatures detection
  - Margin annotations detection
- [ ] Create GitHub issues for v2 features
- [ ] Update project plan timeline

---

## Phase 6: Integration & End-to-End Testing (Weeks 14-15)

**Objective:** Full pipeline integration, E2E tests, performance benchmarking, robustness testing

### Milestone 6.1: Full Pipeline Integration (Week 14)

**Sprint 6.1.1:** Create Integrated Pipeline Orchestrator (4h)
- [ ] Create `src/project_b/pipeline/orchestrator.py`
- [ ] Implement `ProjectBPipeline` class
- [ ] Integrate all modules:
  - Layout detection
  - Reading order prediction
  - OCR orchestration
  - Logical structure assembly
  - Specialized region detection
- [ ] Input: DocumentMetadata + images
- [ ] Output: OCRDocument
- [ ] Write integration tests

**Sprint 6.1.2:** Implement In-Process Integration (from Deployment Model) (3h)
- [ ] Create `src/integrated_pipeline.py` (A→B→C→D stub)
- [ ] Implement `IntegratedRAGPipeline` class
- [ ] Project B integration: `process(DocumentMetadata) → OCRDocument`
- [ ] Write stub integration with mock Project A output
- [ ] Write tests

**Sprint 6.1.3:** Create CLI Interface (3h)
- [ ] Create `src/project_b/cli/main.py` using Click or Typer
- [ ] Commands:
  - `project-b process <metadata.json> <images_dir> --output ocr_document.json`
  - `project-b validate <ocr_document.json>`
  - `project-b health`
- [ ] Write CLI tests

### Milestone 6.2: End-to-End Testing (Week 14-15)

**Sprint 6.2.1:** Create E2E Test Suite (4h)
- [ ] Create `tests/e2e/test_full_pipeline.py`
- [ ] Test cases covering:
  - PDF (image_only, born_digital, hybrid)
  - Office documents (DOCX, XLSX, PPTX)
  - Various layouts (single-column, multi-column, tables, formulas)
  - Various quality levels (high-quality, degraded)
- [ ] Assert OCRDocument.json schema compliance
- [ ] Assert key fields populated correctly

**Sprint 6.2.2:** Run E2E Tests on Validation Dataset (4h)
- [ ] Run E2E tests on 50-100 diverse documents
- [ ] Measure success rate (target: > 95%)
- [ ] Identify failure modes
- [ ] Document results in `docs/validation_reports/phase6_e2e.md`

**Sprint 6.2.3:** Fix Critical E2E Failures (4h per iteration)
- [ ] Analyze top 5 failure modes
- [ ] Fix bugs causing failures
- [ ] Re-run E2E tests
- [ ] Iterate until success rate > 95%

### Milestone 6.3: Performance Benchmarking (Week 15)

**Sprint 6.3.1:** Create Comprehensive Performance Benchmark Suite (4h)
- [ ] Create `scripts/benchmark_full_pipeline.py`
- [ ] Measure end-to-end latency (DocumentMetadata → OCRDocument)
- [ ] Breakdown by module (layout, reading order, OCR, structure)
- [ ] Test on various document sizes (1-page, 10-page, 50-page)
- [ ] Measure throughput (pages/sec)

**Sprint 6.3.2:** Run Performance Benchmarks (3h)
- [ ] Run benchmarks on GPU (primary)
- [ ] Run benchmarks on CPU (fallback)
- [ ] Measure resource usage (GPU memory, CPU, RAM)
- [ ] Document results in `docs/performance_reports/phase6_benchmarks.md`

**Sprint 6.3.3:** Analyze Performance Bottlenecks (3h)
- [ ] Identify slowest modules (profiling with cProfile)
- [ ] Identify memory bottlenecks
- [ ] Identify GPU utilization issues
- [ ] Create optimization backlog (for future iterations)

**Sprint 6.3.4:** Optimize Critical Paths (4h per optimization)
- [ ] Optimize top 3 bottlenecks
- [ ] Re-run benchmarks
- [ ] Verify improvements
- [ ] Iterate until targets met (< 500ms/page avg, > 3 pages/sec)

### Milestone 6.4: Robustness Testing (Week 15)

**Sprint 6.4.1:** Create Fallback Scenario Tests (4h)
- [ ] Test layout detection failure → fallback to simple segmentation
- [ ] Test reading order failure → fallback to spatial ordering
- [ ] Test OCR engine unavailability → fallback to alternate engine
- [ ] Verify graceful degradation (no crashes)
- [ ] Write tests

**Sprint 6.4.2:** Create Stress Tests (3h)
- [ ] Test with very large documents (500+ pages)
- [ ] Test with very small images (< 640x640)
- [ ] Test with corrupted images
- [ ] Test with missing metadata fields
- [ ] Verify error handling

**Sprint 6.4.3:** Test Concurrent Processing (3h)
- [ ] Test multiple documents processed in parallel
- [ ] Verify no race conditions
- [ ] Verify GPU memory doesn't overflow
- [ ] Measure parallel throughput

---

## Phase 7: Benchmarking & Evaluation Refactor (Weeks 16-17)

**Objective:** Refactor existing benchmarking module to new schemas, generate baseline reports

### Milestone 7.1: Benchmarking Module Refactor (Week 16)

**Sprint 7.1.1:** Analyze Legacy Benchmarking Code (3h)
- [ ] Review `src/data_ingestor/benchmarking/orchestrator.py`
- [ ] Review `src/data_ingestor/benchmarking/runner.py`
- [ ] Review `src/data_ingestor/benchmarking/reporter.py`
- [ ] Identify reusable components
- [ ] Document migration plan

**Sprint 7.1.2:** Refactor BenchmarkOrchestrator for New Schemas (4h)
- [ ] Create `src/project_b/benchmarking/orchestrator.py`
- [ ] Adapt to consume DocumentMetadata, output OCRDocument
- [ ] Update dataset loaders (DocLayNet, ROOR, custom)
- [ ] Write tests

**Sprint 7.1.3:** Refactor BenchmarkRunner for New Pipeline (4h)
- [ ] Create `src/project_b/benchmarking/runner.py`
- [ ] Run full Project B pipeline on benchmark datasets
- [ ] Collect metrics (latency, accuracy, resource usage)
- [ ] Write tests

**Sprint 7.1.4:** Refactor BenchmarkReporter for New Metrics (4h)
- [ ] Create `src/project_b/benchmarking/reporter.py`
- [ ] Generate reports for:
  - Layout detection (mAP, per-class AP)
  - Reading order (F1, Kendall's tau)
  - OCR (WER, CER)
  - Tables (TEDS)
  - Performance (latency, throughput)
- [ ] Support HTML, JSON, CSV outputs
- [ ] Write tests

### Milestone 7.2: Baseline Report Generation (Week 16-17)

**Sprint 7.2.1:** Run Full Benchmarks on DocLayNet (4h)
- [ ] Run layout detection + OCR on DocLayNet validation (6,480 pages)
- [ ] May take hours, run overnight or in batches
- [ ] Collect all metrics
- [ ] Save raw results to `results/baseline_doclaynet.json`

**Sprint 7.2.2:** Run Full Benchmarks on ROOR (3h)
- [ ] Run reading order prediction on ROOR dataset
- [ ] Collect F1, Kendall's tau metrics
- [ ] Save results to `results/baseline_roor.json`

**Sprint 7.2.3:** Run Full Benchmarks on Custom Validation Set (3h)
- [ ] Run on custom validation set (50-100 diverse documents)
- [ ] Cover all features (layout, reading order, OCR, tables, formulas)
- [ ] Save results to `results/baseline_custom.json`

**Sprint 7.2.4:** Generate Baseline Reports (4h)
- [ ] Run BenchmarkReporter on all baseline results
- [ ] Generate HTML report (for human review)
- [ ] Generate JSON report (for machine analysis)
- [ ] Generate CSV report (for spreadsheet analysis)
- [ ] Save to `reports/baseline_report_v1.html`

**Sprint 7.2.5:** Analyze Baseline Results (3h)
- [ ] Review baseline report
- [ ] Verify all targets met:
  - Layout: mAP@0.50 ≥ 0.82
  - Reading Order: F1 ≥ 0.85
  - OCR: WER improvement ≥ 10%
  - Tables: TEDS ≥ 0.90
- [ ] Document any shortfalls
- [ ] Create improvement backlog (for v1.1 or v2)

### Milestone 7.3: Comparison with Legacy (Week 17)

**Sprint 7.3.1:** Run Legacy data_ingestor on Same Datasets (4h)
- [ ] Checkout `legacy/data-ingestor-v1` branch
- [ ] Run legacy pipeline on validation datasets
- [ ] Collect metrics (where comparable)
- [ ] Save results to `results/legacy_baseline.json`

**Sprint 7.3.2:** Generate Comparison Report (3h)
- [ ] Create comparison script
- [ ] Compare Project B vs Legacy:
  - OCR quality (WER/CER, if comparable)
  - Processing speed
  - Output schema richness (layout, reading order, structure)
- [ ] Generate comparison report
- [ ] Document improvements and trade-offs

---

## Phase 8: Documentation & Handoff (Week 18)

**Objective:** Update all documentation, create deployment guide, handoff to Project C team

### Milestone 8.1: Documentation Updates (Week 18)

**Sprint 8.1.1:** Update CLAUDE.md (3h)
- [ ] Update Project B architecture section
- [ ] Document new modules (layout, reading_order, ocr, structure, specialized)
- [ ] Update dependencies (YOLOv10-doc, Docling, Marker + Llama 4, DeepSeek-OCR)
- [ ] Update commands (CLI interface)
- [ ] Document resolved open questions

**Sprint 8.1.2:** Update PROJECT_PLAN.md (2h)
- [ ] Mark all phases as COMPLETE
- [ ] Update validation results with actual metrics
- [ ] Document lessons learned
- [ ] Outline v1.1 / v2 roadmap

**Sprint 8.1.3:** Create API Documentation (4h)
- [ ] Generate API docs from docstrings (using Sphinx or MkDocs)
- [ ] Document all public classes and methods
- [ ] Include usage examples
- [ ] Publish to `docs/api/`

**Sprint 8.1.4:** Create Deployment Guide (4h)
- [ ] Create `docs/deployment/README.md`
- [ ] Document installation steps:
  - Poetry setup
  - Dependency installation (GPU vs CPU)
  - Model downloads (YOLOv10-doc, etc.)
  - GCS configuration
  - Modal setup
- [ ] Document configuration options
- [ ] Document Docker deployment
- [ ] Document troubleshooting common issues

**Sprint 8.1.5:** Create Troubleshooting Guide (3h)
- [ ] Create `docs/troubleshooting.md`
- [ ] Document common errors and solutions:
  - CUDA out of memory
  - Model loading failures
  - GCS authentication issues
  - OCR engine timeouts
  - Layout detection failures
- [ ] Include debugging tips
- [ ] Include performance tuning tips

### Milestone 8.2: Integration Documentation for Project C (Week 18)

**Sprint 8.2.1:** Document Input/Output Schemas (3h)
- [ ] Create `docs/integration/project_c_handoff.md`
- [ ] Document DocumentMetadata schema (from Project A)
- [ ] Document OCRDocument schema (to Project C)
- [ ] Provide example JSON files
- [ ] Document GCS image retrieval

**Sprint 8.2.2:** Create Integration Examples (4h)
- [ ] Write example Python code for:
  - Loading DocumentMetadata
  - Calling Project B pipeline
  - Validating OCRDocument
  - Passing to Project C
- [ ] Create Jupyter notebook with examples
- [ ] Save to `docs/integration/examples/`

**Sprint 8.2.3:** Prepare Handoff Meeting (2h)
- [ ] Create handoff presentation slides
- [ ] Prepare demo (live pipeline run)
- [ ] Document open questions for Project C
- [ ] Schedule meeting with Project C team

### Milestone 8.3: Final Validation (Week 18)

**Sprint 8.3.1:** Run Final End-to-End Validation (3h)
- [ ] Run full E2E test suite on fresh validation data
- [ ] Verify all success criteria met
- [ ] Document final validation results
- [ ] Archive results in `docs/validation_reports/final_v1.md`

**Sprint 8.3.2:** Create Release Notes (2h)
- [ ] Document all features in v1.0
- [ ] Document known limitations
- [ ] Document v1.1 / v2 roadmap
- [ ] Create CHANGELOG.md

**Sprint 8.3.3:** Tag Release and Archive (2h)
- [ ] Tag `v1.0.0` in Git
- [ ] Create GitHub release
- [ ] Archive all documentation
- [ ] Archive benchmark results
- [ ] Celebrate! 🎉

---

## Appendix: Sprint Effort Summary

### Total Sprints by Phase

| Phase | Milestones | Sprints | Est. Hours | Est. Weeks |
|-------|------------|---------|------------|------------|
| Phase 0 | 3 | 11 | 35h | 2 weeks |
| Phase 1 | 3 | 15 | 51h | 2 weeks |
| Phase 2 | 5 | 19 | 65h | 2 weeks |
| Phase 3 | 5 | 24 | 88h | 3 weeks |
| Phase 4 | 4 | 13 | 46h | 2 weeks |
| Phase 5 | 3 | 12 | 42h | 2 weeks |
| Phase 6 | 4 | 18 | 62h | 2 weeks |
| Phase 7 | 3 | 13 | 45h | 2 weeks |
| Phase 8 | 3 | 11 | 36h | 1 week |
| **TOTAL** | **33** | **136** | **470h** | **18 weeks** |

**Assumptions:**
- Single developer working 25-30 hours/week on sprints (rest of time: meetings, code review, breaks)
- Each sprint: 3-4 hours focused work
- Buffer time built into week estimates (not all hours are sprint hours)

### Sprint Velocity Tracking

Track actual sprint completion times to adjust estimates:

| Sprint ID | Estimated | Actual | Variance | Notes |
|-----------|-----------|--------|----------|-------|
| S0.1.1 | 3h | TBD | TBD | |
| S0.1.2 | 2h | TBD | TBD | |
| ... | | | | |

---

**Document Status:** DRAFT - Ready for sprint execution

**Prepared By:** Claude Code (AI Assistant)
**Date:** 2025-11-17
**Version:** 1.0.0
**Next Review:** After each milestone completion
