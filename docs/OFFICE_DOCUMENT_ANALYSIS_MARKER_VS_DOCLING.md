# Office Document Processing: Marker vs Docling Analysis

**Date:** 2025-11-17
**Context:** Project B Overhaul - Layout, OCR & Structural Extraction Engine
**Decision Required:** Choose between Marker (with supplemental packages) vs Docling for office document processing

---

## Executive Summary

**Recommendation: Docling (Primary) with Marker (Supplemental for PDFs)**

**Rationale:**
1. **Native Office Support:** Docling has custom-built extensions for DOCX/XLSX/PPTX on top of python-docx/python-pptx/openpyxl
2. **Licensing Alignment:** Docling is MIT-licensed (vs Marker's GPL-3.0), compatible with commercial use
3. **Architecture Alignment:** Docling integrates with DocLayNet (same layout model we're using for PDFs) and TableFormer (97.9% table accuracy)
4. **Project Boundary Clarity:** Docling's modular design better separates Project A (image extraction) from Project B (text/structure extraction)
5. **Maintained & Modern:** Active development, IBM-backed, recent v2 release (Oct 2024), integrations with LangChain/LlamaIndex

**Trade-offs:**
- Marker offers unified processing (all formats through one library), potentially simpler integration
- Marker's LLM-enhanced mode may provide higher accuracy on complex layouts
- Performance comparison needed (both are fast, but specific benchmarks on office documents unclear)

---

## 1. Detailed Comparison

### 1.1 Format Support

#### Marker
```
✅ PDF (primary strength)
✅ DOCX
✅ XLSX
✅ PPTX
✅ Images (JPEG, PNG, TIFF)
✅ HTML
✅ EPUB
```

**Implementation:** Single unified pipeline for all formats

**Source:** [GitHub - datalab-to/marker](https://github.com/datalab-to/marker)

#### Docling
```
✅ PDF
✅ DOCX (via custom python-docx extensions)
✅ XLSX (via custom openpyxl extensions)
✅ PPTX (via custom python-pptx extensions)
✅ Images
✅ HTML
```

**Implementation:** Format-specific parsers with unified output schema

**Source:** [Docling Documentation](https://www.docling.ai/)

**Analysis:**
- **Similar coverage** for formats relevant to Project B
- **Marker**: Unified approach (all formats → single pipeline)
- **Docling**: Specialized approach (per-format optimizations)
- **Winner:** Tie (both support all required formats)

---

### 1.2 Licensing

#### Marker
- **License:** GPL-3.0
- **Implications:**
  - ✅ Free and open-source
  - ⚠️ **Copyleft:** Derivative works must be GPL-3.0
  - ⚠️ Commercial use requires careful compliance (entire application may need to be GPL-3.0)
  - ⚠️ May limit future licensing flexibility for RAG pipeline

**Risk Assessment:** MEDIUM-HIGH
- If data_ingestor/Project B is distributed as a library → GPL-3.0 contamination risk
- If used as internal service → Lower risk (no distribution)
- **Mitigation:** Use as separate microservice with API boundary (no code linking)

#### Docling
- **License:** MIT
- **Implications:**
  - ✅ Free and open-source
  - ✅ Permissive: Can be used in proprietary/commercial applications
  - ✅ No copyleft restrictions
  - ✅ Maximum licensing flexibility

**Risk Assessment:** LOW
- No licensing restrictions on derivative works
- Compatible with commercial deployment

**Winner:** **Docling** (MIT license preferred for commercial flexibility)

---

### 1.3 Table Extraction Capabilities

#### Marker
- **Approach:**
  - Uses vision models to detect tables
  - LLM-enhanced mode (--use_llm flag) can:
    - Merge tables across pages
    - Format tables properly
    - Extract values from forms
- **Output:** Markdown tables, JSON structure
- **Accuracy:** Not explicitly documented for office documents
- **Source:** [Marker Documentation](https://github.com/datalab-to/marker)

**Strengths:**
- LLM enhancement for complex table scenarios
- Cross-page table merging
- Form value extraction

**Weaknesses:**
- Table accuracy metrics not published for office formats
- May require LLM calls (latency, cost)

#### Docling
- **Approach:**
  - **TableFormer model:** State-of-the-art table structure recognition
  - Reassembles rows, columns, spanning cells
  - Native integration with DocLayNet layout model
- **Output:**
  - Pandas DataFrame
  - CSV
  - Structured JSON
- **Accuracy:** **97.9% on PubTables-1M benchmark** (from MODELS.md reference)
- **Source:** [Docling Technical Report (arXiv)](https://arxiv.org/html/2408.09869v4)

**Strengths:**
- **Proven accuracy:** 97.9% table structure recognition
- TableFormer model specifically trained for table extraction
- No LLM required (deterministic, fast, no API costs)
- Native DataFrame output (ideal for Project C)

**Weaknesses:**
- Cross-page table merging not explicitly documented
- Form extraction capabilities unclear

**Winner:** **Docling** (97.9% accuracy, TableFormer model, deterministic)

---

### 1.4 Layout Detection & Reading Order

#### Marker
- **Layout Detection:**
  - Vision-based approach (uses OCR + layout analysis)
  - Not explicitly using DocLayNet classes
- **Reading Order:**
  - Inferred from document structure
  - LLM-enhanced mode can improve reading order
- **Output:** Markdown (preserves structure via headings, lists, etc.)

**Alignment with Project B Requirements:**
- ⚠️ **Indirect alignment:** Marker doesn't expose 11 DocLayNet classes directly
- ⚠️ Reading order embedded in Markdown (not explicit block-level ordering)
- ⚠️ Would require post-processing to extract layout_blocks[] and reading_order[] for OCRDocument.json schema

**Integration Complexity:** MEDIUM-HIGH
- Need to reverse-engineer Markdown → layout blocks
- Need to infer reading order from Markdown structure
- May lose spatial information (bboxes)

#### Docling
- **Layout Detection:**
  - **DocLayNet model:** Same 11-class layout model we're using for PDFs
  - Bounding boxes in COCO format
  - Confidence scores per element
- **Reading Order:**
  - Built-in reading order prediction
  - Respects document structure (headings, sections, tables, figures)
- **Output:** Unified DoclingDocument model with:
  - Layout elements (class labels, bboxes)
  - Reading order sequence
  - Hierarchical structure (headings, sections)

**Alignment with Project B Requirements:**
- ✅ **Direct alignment:** Docling uses DocLayNet (same as our PDF pipeline)
- ✅ Exposes layout_blocks[] with class_label, bbox, confidence
- ✅ Native reading order prediction
- ✅ Output schema maps directly to OCRDocument.json

**Integration Complexity:** LOW
- DoclingDocument → OCRDocument.json is straightforward mapping
- Minimal post-processing needed
- Consistent with PDF processing pipeline

**Winner:** **Docling** (DocLayNet integration, direct schema mapping)

---

### 1.5 Text Extraction Quality

#### Marker
- **OCR Approach:**
  - Uses Surya OCR for PDFs/images
  - Native text extraction for office documents (via library parsing)
- **LLM Enhancement (--use_llm flag):**
  - Improves inline math extraction
  - Fixes table formatting
  - Merges fragmented text
- **Output Quality:**
  - Markdown format (clean, human-readable)
  - Preserves emphasis (bold, italic)
  - Code blocks, links, references

**Strengths:**
- LLM-enhanced mode for complex layouts
- Clean Markdown output
- Good for PDFs (our primary use case in current system)

**Weaknesses:**
- Office document text extraction quality not explicitly benchmarked
- LLM enhancement adds latency/cost

#### Docling
- **Text Extraction:**
  - Native parsing of DOCX/XLSX/PPTX via python-docx/python-pptx/openpyxl
  - Preserves formatting, styles, metadata
  - OCR for embedded images (if needed)
- **Output Quality:**
  - Structured JSON/HTML/Markdown
  - Full document hierarchy (headings, sections, paragraphs)
  - Metadata preservation (authors, dates, styles)

**Strengths:**
- Native office format parsing (no OCR needed for digital text)
- Format-specific optimizations (custom extensions on python-docx/pptx/openpyxl)
- Full metadata preservation

**Weaknesses:**
- No LLM enhancement option (deterministic only)

**Winner:** **Docling** (native office format parsing, no OCR needed for digital text)

---

### 1.6 Performance

#### Marker
- **Throughput:** 25 pages/sec on H100 GPU (batch mode)
- **Latency:** Not explicitly documented for office documents
- **Resource Usage:**
  - GPU-accelerated (optional)
  - LLM mode requires API calls or local LLM
- **Benchmarks:** Primarily focused on PDF performance

**Source:** [Marker Performance Claims](https://github.com/datalab-to/marker)

**Estimated Performance (Office Docs):**
- Native text extraction should be fast (< 100ms per document)
- LLM enhancement adds ~500-2000ms depending on document size

#### Docling
- **Throughput:** Not explicitly published (depends on document complexity)
- **Latency:** Fast for native office formats (< 100ms estimated)
- **Resource Usage:**
  - CPU-based for office documents (no GPU needed)
  - TableFormer model runs on GPU (optional)
- **Benchmarks:** Focused on accuracy (97.9% table extraction)

**Estimated Performance (Office Docs):**
- DOCX/XLSX/PPTX parsing: < 100ms per document (native libraries)
- TableFormer inference: ~50-100ms per table (GPU)
- Reading order prediction: < 50ms per page

**Winner:** **Tie** (both are fast for office documents; specific benchmarks needed)

---

### 1.7 Integration with Project B Architecture

#### Marker Integration

**Pros:**
- ✅ Unified processing: Same library for PDF + Office documents
- ✅ Already familiar (current system uses Marker for PDFs)
- ✅ Simpler dependency management (one library instead of multiple)

**Cons:**
- ⚠️ GPL-3.0 licensing risk (needs careful isolation)
- ⚠️ **Schema mismatch:** Marker outputs Markdown, not layout blocks
- ⚠️ **Post-processing required:** Need to extract layout_blocks[], reading_order[] from Markdown
- ⚠️ May not expose 11 DocLayNet classes explicitly (custom mapping needed)
- ⚠️ LLM enhancement mode conflicts with Project B's deterministic approach

**Integration Effort:** MEDIUM-HIGH
```python
# Marker integration (conceptual)
def process_office_document_marker(metadata: DocumentMetadata) -> OCRDocument:
    # 1. Use Marker to convert DOCX → Markdown
    markdown_output = marker.convert(metadata.source_path)

    # 2. PROBLEM: Need to extract layout blocks from Markdown
    #    - Parse Markdown AST (headings, tables, lists, paragraphs)
    #    - Infer bboxes (NOT available in Markdown)
    #    - Map Markdown elements → DocLayNet classes (custom logic)
    layout_blocks = extract_layout_from_markdown(markdown_output)  # Custom code

    # 3. PROBLEM: Reading order embedded in Markdown sequence
    #    - Markdown is sequential by nature, but need explicit indices
    reading_order = infer_reading_order(layout_blocks)  # Custom code

    # 4. PROBLEM: Multi-engine OCR not applicable (office docs have native text)
    #    - Marker extracts text directly (no OCR needed)
    #    - Can't run DeepSeek-OCR for validation (no image regions)

    # 5. Convert to OCRDocument schema
    return OCRDocument(
        layout_blocks=layout_blocks,
        reading_order=reading_order,
        paragraphs=extract_paragraphs(markdown_output)  # Custom code
    )
```

**Key Challenges:**
1. **No bboxes:** Markdown doesn't preserve spatial information
2. **Schema impedance mismatch:** Markdown → OCRDocument.json requires custom translation layer
3. **Inconsistent with PDF pipeline:** PDFs use layout detection, office docs use Markdown parsing
4. **Limited multi-engine support:** Can't apply OCR orchestration to native text

#### Docling Integration

**Pros:**
- ✅ **Direct schema mapping:** DoclingDocument → OCRDocument.json (minimal transformation)
- ✅ **Consistent with PDF pipeline:** Same DocLayNet classes, same layout approach
- ✅ **MIT license:** No GPL-3.0 contamination risk
- ✅ **Modular architecture:** Separate parsers for DOCX/XLSX/PPTX (follows Project B design)
- ✅ **Native bboxes:** Spatial information preserved
- ✅ **TableFormer integration:** 97.9% table accuracy

**Cons:**
- ⚠️ New library (learning curve, less familiar than Marker)
- ⚠️ May require separate pipeline for office documents vs PDFs (but this aligns with Project B design)
- ⚠️ No LLM enhancement option (but Project B doesn't require this)

**Integration Effort:** LOW-MEDIUM
```python
# Docling integration (conceptual)
def process_office_document_docling(metadata: DocumentMetadata) -> OCRDocument:
    # 1. Use Docling to parse DOCX
    docling_doc = docling.parse(metadata.source_path)

    # 2. Extract layout blocks (DIRECT MAPPING)
    layout_blocks = [
        LayoutBlock(
            block_id=elem.id,
            class_label=elem.label,  # DocLayNet classes (same as PDFs!)
            bbox=elem.bbox,  # COCO format
            confidence=elem.confidence,
            reading_order_index=elem.reading_order
        )
        for elem in docling_doc.layout_elements
    ]

    # 3. Reading order (ALREADY COMPUTED)
    reading_order = docling_doc.reading_order  # Native support

    # 4. Extract paragraphs (DIRECT MAPPING)
    paragraphs = [
        Paragraph(
            paragraph_id=para.id,
            layout_block_id=para.layout_block_id,
            heading_path=para.heading_path,  # Already computed!
            structural_role=para.structural_role,  # Already classified!
            ocr_engines={
                "docling": {
                    "text": para.text,
                    "confidence": 1.0  # Native text, not OCR
                }
            }
        )
        for para in docling_doc.paragraphs
    ]

    # 5. Convert to OCRDocument schema (STRAIGHTFORWARD)
    return OCRDocument(
        layout_blocks=layout_blocks,
        reading_order=reading_order,
        paragraphs=paragraphs
    )
```

**Key Advantages:**
1. **Native bboxes:** Spatial information preserved
2. **DocLayNet consistency:** Same 11 classes as PDF pipeline
3. **Reading order included:** No custom inference needed
4. **Heading paths included:** Logical structure pre-computed
5. **Minimal transformation:** DoclingDocument → OCRDocument.json is straightforward

**Winner:** **Docling** (direct schema mapping, consistent with PDF pipeline, lower integration effort)

---

### 1.8 Alignment with Project A/B Boundary

Recall from the reference docs:
- **Project A** handles: Embedded image extraction from office documents
- **Project B** handles: Text extraction and structure parsing

#### Marker Approach
```
Project A: Extract embedded images (?)
    ↓
Marker: Convert entire DOCX → Markdown (text + structure)
    ↓
Project B: Parse Markdown → OCRDocument.json (?)
```

**Boundary Ambiguity:**
- ⚠️ Marker does both image extraction AND text extraction (blurs A/B boundary)
- ⚠️ If Marker runs in Project A → Project B has nothing to do (violates separation of concerns)
- ⚠️ If Marker runs in Project B → How does Project A extract images?

**Recommendation:** Would need to split Marker's processing across A/B, adding complexity

#### Docling Approach
```
Project A: Docling.extract_images(docx) → Embedded images
    ↓ (Images go to IQA pipeline)
    ↓
Project B: Docling.parse_structure(docx) → DoclingDocument → OCRDocument.json
    ↓
Project C: Multi-engine fusion, RAG chunking
```

**Boundary Clarity:**
- ✅ **Clear separation:** Project A extracts images, Project B extracts text/structure
- ✅ **Modular:** Docling has separate APIs for image extraction vs document parsing
- ✅ **Consistent with reference docs:** "Docling integration scope for Project A (image extraction only), Project B (text extraction)"

**Winner:** **Docling** (clear A/B boundary, consistent with architecture)

---

### 1.9 Multi-Engine OCR Support (Project B Requirement)

#### Marker
- **Native Text:** Office documents have digital text (no OCR needed)
- **Multi-Engine Support:** Not applicable (no OCR for native text)
- **Fallback:** If embedded images need OCR → Marker can handle, but doesn't support multi-engine comparison

**Alignment with Project B FR-B3 (OCR Orchestration):**
- ⚠️ **Poor alignment:** Can't run Marker + DeepSeek-OCR on native text
- ⚠️ Multi-engine OCR only applies to embedded images (handled by Project A)
- ⚠️ Office documents would bypass OCR orchestration logic

#### Docling
- **Native Text:** Office documents have digital text (no OCR needed)
- **Multi-Engine Support:** Not applicable for native text
- **Embedded Images:** If images need OCR → Project A handles via Marker/DeepSeek-OCR

**Alignment with Project B FR-B3 (OCR Orchestration):**
- ✅ **Consistent:** Native text bypasses OCR (expected behavior)
- ✅ **Embedded images handled upstream:** Project A applies OCR to images, Project B consumes results
- ✅ **Clear boundary:** OCR is Project B's job only when needed (not for native office text)

**Winner:** **Tie** (multi-engine OCR not applicable to native office text in both cases)

---

### 1.10 Maintenance & Community

#### Marker
- **Maintainer:** datalab-to (commercial entity)
- **GitHub Stars:** ~21k+ (very popular)
- **Last Update:** Active (regular commits as of 2024/2025)
- **Community:** Large, active community
- **Documentation:** Good (GitHub README, examples)
- **Integrations:** LangChain, LlamaIndex support

**Health:** ✅ Very healthy, actively maintained

#### Docling
- **Maintainer:** IBM Research (Deep Search team)
- **GitHub Stars:** ~10k+ (growing rapidly)
- **Last Update:** Very active (v2 released Oct 2024)
- **Community:** Growing rapidly (backed by IBM)
- **Documentation:** Excellent (arXiv papers, technical reports, tutorials)
- **Integrations:** LangChain, LlamaIndex, Haystack support

**Health:** ✅ Very healthy, enterprise-backed

**Winner:** **Tie** (both are actively maintained, healthy projects)

---

## 2. Alignment with Project B Requirements

### Summary Table

| Requirement | Marker | Docling | Winner |
|-------------|--------|---------|--------|
| **FR-B1: Layout Detection** | ⚠️ Indirect (Markdown) | ✅ DocLayNet (direct) | **Docling** |
| **FR-B2: Reading Order** | ⚠️ Embedded in Markdown | ✅ Native support | **Docling** |
| **FR-B3: OCR Orchestration** | N/A (native text) | N/A (native text) | Tie |
| **FR-B4: Structure Assembly** | ⚠️ Custom extraction | ✅ Pre-computed | **Docling** |
| **FR-B5: Specialized Regions** | ⚠️ Limited | ✅ TableFormer | **Docling** |
| **NFR-B1: Performance** | ✅ 25 pages/sec (PDF) | ✅ Fast (estimated) | Tie |
| **NFR-B2: Robustness** | ✅ LLM fallback | ✅ Deterministic | Tie |
| **NFR-B3: Logging** | ✅ Supported | ✅ Supported | Tie |
| **Licensing** | ⚠️ GPL-3.0 | ✅ MIT | **Docling** |
| **Schema Alignment** | ⚠️ Poor (Markdown) | ✅ Excellent | **Docling** |
| **Table Accuracy** | Unknown | ✅ 97.9% (TEDS) | **Docling** |
| **Integration Effort** | Medium-High | Low-Medium | **Docling** |
| **A/B Boundary Clarity** | ⚠️ Ambiguous | ✅ Clear | **Docling** |

**Overall Winner:** **Docling** (9 wins vs 0 wins for Marker, 4 ties)

---

## 3. Recommended Architecture

### 3.1 Hybrid Approach: Docling (Office) + Marker (PDF)

```
┌─────────────────────────────────────────────────────────────┐
│                      Project B Pipeline                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Input: DocumentMetadata.json                                │
│         ↓                                                     │
│  ┌──────────────────┐                                        │
│  │ Format Router    │                                        │
│  └────────┬─────────┘                                        │
│           │                                                   │
│           ├─── PDF? ───────→ Marker + Llama 4 (primary)      │
│           │                  DeepSeek-OCR (secondary)        │
│           │                  ↓                                │
│           │                  Layout Detection (YOLOv10-doc)  │
│           │                  ↓                                │
│           │                  Reading Order Predictor         │
│           │                  ↓                                │
│           │                  OCRDocument.json                 │
│           │                                                   │
│           └─── DOCX/XLSX/PPTX? ──→ Docling Parser            │
│                                     ↓                         │
│                                     DoclingDocument           │
│                                     ↓                         │
│                                     OCRDocument.json          │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Separation of Concerns (Project A vs Project B)

**Project A (Image Preprocessing):**
- Office documents → Docling.extract_images() → Embedded images
- Images → IQA pipeline (blur, noise, contrast, corrections)
- Images → Stored in S3/GCS, paths in DocumentMetadata.json

**Project B (Layout & OCR):**
- PDFs → Marker + YOLOv10-doc → OCRDocument.json
- Office documents → Docling.parse_structure() → OCRDocument.json
- Both paths produce consistent OCRDocument.json schema

**Project C (Fusion & Chunking):**
- OCRDocument.json → Multi-engine fusion (if applicable)
- Paragraphs → RAG chunks

### 3.3 Implementation Plan

**Phase 0 (Weeks 1-2): Foundation**
- Install Docling library: `pip install docling`
- Define Docling → OCRDocument.json mapping
- Create sample test data (DOCX, XLSX, PPTX files)
- Validate schema compliance

**Phase 3 (Weeks 7-9): OCR Orchestration**
- Integrate Marker for PDFs (existing)
- **Integrate Docling for Office documents (NEW)**
- Create format router (PDF → Marker, Office → Docling)
- Implement Docling → OCRDocument.json converter

**Phase 6 (Weeks 14-15): Integration Testing**
- E2E tests with DOCX/XLSX/PPTX files
- Validate layout blocks, reading order, table extraction
- Performance benchmarking (latency, throughput)

---

## 4. Risk Analysis

### 4.1 Risks of Choosing Marker

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **GPL-3.0 licensing contamination** | High | High | Isolate Marker in separate microservice, API boundary |
| **Schema mismatch (Markdown vs OCRDocument)** | High | High | Write custom Markdown → layout blocks converter (high effort) |
| **Inconsistent with PDF pipeline** | High | Medium | Accept dual approach (Marker for PDF, custom for office) |
| **Missing bboxes in Markdown** | High | High | Workaround: Infer bboxes from Markdown AST (inaccurate) |
| **No TableFormer accuracy** | Medium | Medium | Accept lower table accuracy for office docs |

**Overall Risk:** HIGH

### 4.2 Risks of Choosing Docling

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Learning curve (new library)** | Medium | Low | Well-documented, active community, IBM support |
| **Performance unknown for large docs** | Low | Medium | Benchmark on test dataset, optimize if needed |
| **Dual library maintenance** | Low | Low | Both Marker + Docling are actively maintained |
| **No LLM enhancement option** | Low | Low | Not required for Project B deterministic approach |

**Overall Risk:** LOW

---

## 5. Final Recommendation

### ✅ Choose Docling for Office Documents

**Reasons:**
1. **Direct Schema Alignment:** DoclingDocument → OCRDocument.json is straightforward
2. **DocLayNet Consistency:** Same 11 layout classes as PDF pipeline
3. **MIT License:** No GPL-3.0 contamination risk
4. **Table Accuracy:** 97.9% with TableFormer model
5. **Clear A/B Boundary:** Docling supports separate image extraction (A) vs text extraction (B)
6. **Lower Integration Effort:** Native bboxes, reading order, heading paths pre-computed
7. **Active Maintenance:** IBM-backed, recent v2 release, growing community
8. **Native Office Parsing:** Custom extensions on python-docx/pptx/openpyxl

### ✅ Keep Marker for PDFs

**Reasons:**
1. **Proven Performance:** 25 pages/sec, already familiar
2. **OCR Capabilities:** Surya OCR for scanned PDFs
3. **LLM Enhancement:** Optional accuracy boost for complex layouts
4. **Existing Integration:** Current system uses Marker (lower migration risk)

### 🔄 Hybrid Architecture

```
Project B Format Router:
├── PDF → Marker + YOLOv10-doc + DeepSeek-OCR → OCRDocument.json
└── DOCX/XLSX/PPTX → Docling → OCRDocument.json
```

Both paths produce consistent OCRDocument.json schema for Project C.

---

## 6. Next Steps

### Immediate Actions (Week 1)
1. ✅ **Approve Docling for office documents**
2. ✅ **Approve hybrid architecture (Docling + Marker)**
3. ✅ Install Docling: `pip install docling`
4. ✅ Create Docling → OCRDocument.json mapper (prototype)
5. ✅ Test on sample DOCX/XLSX/PPTX files
6. ✅ Validate TableFormer accuracy on test dataset

### Short-Term (Weeks 2-4)
1. Implement format router (PDF vs Office document detection)
2. Integrate Docling parser for DOCX/XLSX/PPTX
3. Write unit tests (Docling → OCRDocument.json conversion)
4. Benchmark performance (latency, throughput)

### Medium-Term (Weeks 7-9)
1. Integrate with OCR orchestration pipeline (Phase 3)
2. E2E testing with real-world office documents
3. Validate schema compliance (100% OCRDocument.json conformance)
4. Performance optimization (if needed)

---

## Appendix A: Code Samples

### A.1 Docling Integration (Conceptual)

```python
from docling import Docling
from project_b.schemas.ocr_document import OCRDocument, LayoutBlock, Paragraph

def process_office_document(metadata: DocumentMetadata) -> OCRDocument:
    """Process DOCX/XLSX/PPTX using Docling."""

    # 1. Initialize Docling
    docling = Docling()

    # 2. Parse document
    doc = docling.parse(metadata.source_path)

    # 3. Extract layout blocks (DocLayNet classes)
    layout_blocks = [
        LayoutBlock(
            block_id=f"p{page_idx}_b{block_idx}",
            class_label=block.label,  # DocLayNet: text, table, title, etc.
            bbox=block.bbox,  # COCO format [x, y, width, height]
            confidence=block.confidence,
            reading_order_index=block.reading_order
        )
        for page_idx, page in enumerate(doc.pages)
        for block_idx, block in enumerate(page.layout_elements)
    ]

    # 4. Extract reading order (pre-computed by Docling)
    reading_order = [
        block.id
        for page in doc.pages
        for block in sorted(page.layout_elements, key=lambda x: x.reading_order)
    ]

    # 5. Extract paragraphs (with heading paths)
    paragraphs = [
        Paragraph(
            paragraph_id=f"p{page_idx}_para{para_idx}",
            page_index=page_idx,
            layout_block_id=para.layout_block_id,
            heading_path=para.heading_path,  # Already computed!
            structural_role=para.structural_role,  # Already classified!
            reading_order_index=para.reading_order,
            ocr_engines={
                "docling": {
                    "text": para.text,
                    "confidence": 1.0  # Native text, not OCR
                }
            },
            languages=metadata.languages,
            has_math=para.has_math,
            has_table_ref=para.has_table_ref,
            has_handwriting=False  # Office docs are digital
        )
        for page_idx, page in enumerate(doc.pages)
        for para_idx, para in enumerate(page.paragraphs)
    ]

    # 6. Assemble OCRDocument
    return OCRDocument(
        schema_version="1.0.0",
        document_id=metadata.document_id,
        page_count=len(doc.pages),
        layout_model_name="docling_doclaynet_v2",
        ocr_engines=["docling"],
        pages=[
            {
                "page_index": idx,
                "width_px": page.width,
                "height_px": page.height,
                "layout_blocks": [b for b in layout_blocks if b.page_index == idx],
                "reading_order": [b.id for b in layout_blocks if b.page_index == idx],
                "paragraphs": [p for p in paragraphs if p.page_index == idx]
            }
            for idx, page in enumerate(doc.pages)
        ]
    )
```

### A.2 Format Router (Conceptual)

```python
def route_document(metadata: DocumentMetadata) -> OCRDocument:
    """Route to appropriate processor based on document type."""

    if metadata.document_type == "pdf":
        # Use Marker + YOLOv10-doc pipeline
        return process_pdf_document(metadata)

    elif metadata.document_type in ["office_word", "office_excel", "office_powerpoint"]:
        # Use Docling pipeline
        return process_office_document(metadata)

    else:
        raise UnsupportedFormatError(f"Unsupported format: {metadata.document_type}")
```

---

## Appendix B: References

### Docling Resources
- [Docling GitHub](https://github.com/docling-project/docling)
- [Docling Technical Report (arXiv)](https://arxiv.org/html/2408.09869v4)
- [Docling Official Site](https://www.docling.ai/)
- [Docling IBM Announcement](https://research.ibm.com/publications/docling-an-efficient-open-source-toolkit-for-ai-driven-document-conversion)

### Marker Resources
- [Marker GitHub](https://github.com/datalab-to/marker)
- [Marker PyPI](https://pypi.org/project/marker-pdf/)
- [Marker Performance Benchmarks](https://github.com/datalab-to/marker#benchmarks)

### Project B References
- [Project B Overhaul Plan](/home/user/data_ingestor/docs/PROJECT_B_OVERHAUL_PLAN.md)
- [Project B F/NF Requirements](/home/user/data_ingestor/docs/Ref Docs/RAG Pipeline/project-b-f-nf.md)
- [Project A F/NF Requirements](/home/user/data_ingestor/docs/Ref Docs/RAG Pipeline/Project_A_F_NF.md)
- [Models Overview](/home/user/data_ingestor/docs/Ref Docs/RAG Pipeline/MODELS.md)

---

**Document Status:** DRAFT - Awaiting approval
**Prepared By:** Claude Code (AI Assistant)
**Date:** 2025-11-17
**Next Review:** Week 1 decision on office document processing approach
