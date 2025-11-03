# RAG Data Ingestion Pipeline - Project Plan

**Project Name**: Data Ingestor
**Version**: 1.0
**Status**: Phase 1 - Foundation (In Progress)
**Last Updated**: 2025-11-02
**Owner**: Byron Williams

---

## Executive Summary

The Data Ingestor is a scalable, extensible data ingestion pipeline that transforms diverse document formats (PDF, DOCX, HTML, Video, Audio) into high-quality, RAG-ready structured data with intelligent chunking and metadata preservation. This project replaces commercial solutions like unstructured.io with an open-source alternative using tools available under permissive licenses (e.g., Marker's small revenue exception).

### Mission Statement

Build a production-grade data ingestion pipeline that:
1. Supports multiple document formats with extensible architecture
2. Provides high-quality text extraction (>90% accuracy)
3. Implements intelligent chunking strategies for optimal RAG performance
4. Scales to process 1000+ documents per hour
5. Maintains reliability with <1% failure rate

---

## Table of Contents

1. [Requirements Specification](#requirements-specification)
2. [Architecture Design](#architecture-design)
3. [Implementation Phases](#implementation-phases)
4. [Traceability Matrix](#traceability-matrix)
5. [Success Criteria](#success-criteria)
6. [Risk Management](#risk-management)
7. [Testing Strategy](#testing-strategy)

---

## Requirements Specification

### 1. Functional Requirements

#### FR-1: Document Format Support

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-1.1 | Support PDF document processing | P0 | ✅ Implemented |
| FR-1.2 | Support DOCX document processing | P1 | ⏳ Planned (Phase 2) |
| FR-1.3 | Support HTML/Website content | P1 | ⏳ Planned (Phase 2) |
| FR-1.4 | Support Video transcription | P2 | ⏳ Planned (Phase 2) |
| FR-1.5 | Support Audio transcription | P2 | ⏳ Planned (Phase 2) |
| FR-1.6 | Support academic paper metadata extraction | P2 | ⏳ Planned (Phase 2) |

**Acceptance Criteria (FR-1.1 - PDF)**:
- Must extract text from native PDFs with >90% accuracy
- Must preserve document structure (headings, paragraphs, lists)
- Must extract tables as structured data with >85% accuracy
- Must handle scanned PDFs with OCR
- Must support multi-language documents (minimum 20 languages)
- Must extract metadata (title, author, date, page count)

#### FR-2: Parser Management

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-2.1 | Automatic format detection from file path | P0 | ✅ Implemented |
| FR-2.2 | Parser registry with priority ordering | P0 | ✅ Implemented |
| FR-2.3 | Automatic fallback to secondary parsers on failure | P0 | ✅ Implemented |
| FR-2.4 | Parser health checking | P1 | ✅ Implemented |
| FR-2.5 | Configurable parser selection per format | P1 | ✅ Implemented |
| FR-2.6 | Support for custom parser plugins | P2 | ⏳ Planned (Phase 5) |

**Acceptance Criteria (FR-2.3 - Fallback)**:
- Must attempt all registered parsers in priority order
- Must provide detailed error information when all parsers fail
- Must track which parser succeeded for each document
- Must log fallback attempts for monitoring

#### FR-3: Document Chunking

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-3.1 | Token-based chunking with configurable size | P0 | ✅ Implemented |
| FR-3.2 | Configurable chunk overlap | P0 | ✅ Implemented |
| FR-3.3 | Table preservation (no splitting) | P0 | ✅ Implemented |
| FR-3.4 | Element-based chunking strategy | P1 | ⏳ Planned (Phase 3) |
| FR-3.5 | Semantic-aware chunking | P2 | ⏳ Planned (Phase 5) |
| FR-3.6 | Context window preservation | P1 | ⏳ Planned (Phase 3) |

**Acceptance Criteria (FR-3.1 - Token Chunking)**:
- Must support configurable chunk size (default: 1000 tokens)
- Must support configurable overlap (default: 200 tokens)
- Must handle large elements that exceed chunk size
- Must preserve metadata for each chunk
- Must provide accurate token counts using tiktoken

#### FR-4: Data Quality

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-4.1 | Quality score calculation per document | P1 | ⏳ Planned (Phase 3) |
| FR-4.2 | Configurable quality thresholds | P1 | ⏳ Planned (Phase 3) |
| FR-4.3 | Automatic flagging for human review | P1 | ⏳ Planned (Phase 3) |
| FR-4.4 | Extraction completeness metrics | P1 | ⏳ Planned (Phase 3) |
| FR-4.5 | Structure preservation validation | P2 | ⏳ Planned (Phase 3) |

**Acceptance Criteria (FR-4.1 - Quality Scoring)**:
- Must calculate overall quality score (0.0-1.0)
- Must track text extraction completeness
- Must track structure preservation accuracy
- Must track table extraction accuracy
- Must categorize quality level (Excellent, Good, Marginal, Poor)

#### FR-5: Storage & Persistence

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-5.1 | Document metadata storage in database | P1 | ⏳ Planned (Phase 3) |
| FR-5.2 | File system storage for processed documents | P1 | ⏳ Planned (Phase 3) |
| FR-5.3 | Hash-based deduplication | P1 | ✅ Implemented |
| FR-5.4 | Vector store integration | P1 | ⏳ Planned (Phase 4) |
| FR-5.5 | S3-compatible storage support | P2 | ⏳ Planned (Phase 4) |
| FR-5.6 | Document versioning | P2 | ⏳ Planned (Phase 4) |

#### FR-6: APIs & Interfaces

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-6.1 | Command-line interface for single document processing | P0 | ✅ Implemented |
| FR-6.2 | CLI health check command | P0 | ✅ Implemented |
| FR-6.3 | REST API for document submission | P1 | ⏳ Planned (Phase 2) |
| FR-6.4 | REST API for batch processing | P1 | ⏳ Planned (Phase 2) |
| FR-6.5 | Async task status checking | P1 | ⏳ Planned (Phase 3) |
| FR-6.6 | Python SDK | P2 | ✅ Implemented (native API) |
| FR-6.7 | Web UI for management | P3 | ⏳ Planned (Phase 5) |

#### FR-7: Output Formats & Export

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-7.1 | JSON export with full metadata | P0 | ⏳ In Progress (Phase 1) |
| FR-7.2 | Markdown export with preserved structure | P0 | ⏳ In Progress (Phase 1) |
| FR-7.3 | Dual format export (JSON + Markdown) | P0 | ⏳ In Progress (Phase 1) |
| FR-7.4 | Metadata preservation in front matter | P1 | ⏳ In Progress (Phase 1) |
| FR-7.5 | CSV export for tabular data | P2 | ⏳ Planned (Phase 2) |
| FR-7.6 | HTML export with styling | P3 | ⏳ Planned (Phase 3) |

**Acceptance Criteria (FR-7.2 - Markdown Export)**:
- Must preserve document structure (headings, lists, tables)
- Must include metadata as YAML front matter
- Must maintain text emphasis (bold, italic)
- Must handle tables with proper markdown syntax
- Must support LLM-friendly formatting
- Must preserve element hierarchy

**Acceptance Criteria (FR-7.3 - Dual Export)**:
- Must export both JSON and Markdown from single command
- Must ensure content consistency between formats
- Must preserve all metadata in both formats
- Must support streaming export for large documents

#### FR-8: Enhanced Metadata & Enrichment

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-8.1 | Coordinate tracking (bounding boxes) | P1 | ⏳ In Progress (Phase 1) |
| FR-8.2 | Hierarchy tracking (parent_id, depth) | P1 | ⏳ In Progress (Phase 1) |
| FR-8.3 | Text emphasis preservation (bold, italic) | P1 | ⏳ In Progress (Phase 1) |
| FR-8.4 | Model confidence scores | P1 | ⏳ In Progress (Phase 1) |
| FR-8.5 | Image extraction as Base64 | P0 | ⏳ Planned (Multimodal Phase 1) |
| FR-8.6 | Custom regex metadata extraction | P2 | ⏳ Planned (Phase 3) |
| FR-8.7 | LLM-based image descriptions | P0 | ⏳ Planned (Multimodal Phase 2) |
| FR-8.8 | Table summarization | P0 | ⏳ Planned (Multimodal Phase 2) |
| FR-8.9 | Named Entity Recognition (NER) | P3 | ⏳ Planned (Phase 5) |

#### FR-10: Multimodal RAG (Based on Alejandro AO's Architecture)

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-10.1 | Image extraction from PDFs as Base64 | P0 | ⏳ Planned (Multimodal Phase 1) |
| FR-10.2 | Summary generation for text content | P0 | ⏳ Planned (Multimodal Phase 2) |
| FR-10.3 | Summary generation for tables | P0 | ⏳ Planned (Multimodal Phase 2) |
| FR-10.4 | Vision LLM-based image descriptions | P0 | ⏳ Planned (Multimodal Phase 2) |
| FR-10.5 | Summary-based embedding (embed summaries, not raw content) | P0 | ⏳ Planned (Multimodal Phase 2) |
| FR-10.6 | Multi-vector store architecture (Qdrant + Document Store) | P0 | ⏳ Planned (Multimodal Phase 3) |
| FR-10.7 | Two-stage retrieval (search summaries, fetch originals) | P0 | ⏳ Planned (Multimodal Phase 3) |
| FR-10.8 | Multimodal LLM integration (Claude 3.5 Sonnet) | P0 | ⏳ Planned (Multimodal Phase 4) |
| FR-10.9 | RAG query engine with image + text + table support | P0 | ⏳ Planned (Multimodal Phase 4) |
| FR-10.10 | Conversation memory for multi-turn dialogues | P1 | ⏳ Planned (Multimodal Phase 4) |
| FR-10.11 | Source citation with provenance tracking | P1 | ⏳ Planned (Multimodal Phase 4) |
| FR-10.12 | Gradio demo interface for interactive exploration | P2 | ⏳ Planned (Multimodal Phase 4) |

**Acceptance Criteria (FR-10.1 - Image Extraction)**:
- Must extract images from PDFs as Base64-encoded data
- Must preserve image metadata (size, format, position)
- Must handle multiple image formats (JPEG, PNG, TIFF)
- Must integrate with all three PDF parsers (PyMuPDF, PyMuPDF4LLM, Marker)
- Must gracefully handle corrupted or encrypted images

**Acceptance Criteria (FR-10.5 - Summary-Based Embedding)**:
- Must generate concise summaries (50-200 words) for all content types
- Must embed summaries instead of raw content for retrieval
- Must maintain link between summaries and original content
- Summary generation <2s per chunk
- Embedding quality improvement >15% vs. raw content embedding

**Acceptance Criteria (FR-10.6 - Multi-Vector Store)**:
- Must separate vector store (Qdrant) from document store
- Must link summaries to originals via chunk_id
- Must support batch operations (1000+ chunks)
- Retrieval must return original content, not summaries
- Must preserve all metadata through storage/retrieval

**Acceptance Criteria (FR-8.1 - Coordinates)**:
- Must capture bounding box for all visual elements
- Must support coordinate system transformation
- Must preserve spatial relationships
- Must enable visual rendering capabilities

**Acceptance Criteria (FR-8.2 - Hierarchy)**:
- Must track parent-child relationships
- Must calculate category depth
- Must support nested structures (lists, sections)
- Must enable structure-aware queries

#### FR-9: Source & Destination Connectors

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-9.1 | S3-compatible storage source | P2 | ⏳ Planned (Phase 4) |
| FR-9.2 | Google Drive source connector | P2 | ⏳ Planned (Phase 4) |
| FR-9.3 | Dropbox source connector | P3 | ⏳ Planned (Phase 5) |
| FR-9.4 | SharePoint source connector | P3 | ⏳ Planned (Phase 5) |
| FR-9.5 | Batch processing from connectors | P2 | ⏳ Planned (Phase 4) |

### 2. Non-Functional Requirements

#### NFR-1: Performance

| ID | Requirement | Target | Status |
|----|-------------|--------|--------|
| NFR-1.1 | Process 1000+ mixed documents per hour | 1000 docs/hr | ⏳ To be tested |
| NFR-1.2 | Single document processing time <1 minute | <60s | ⏳ To be tested |
| NFR-1.3 | Memory usage per worker <2GB | <2GB | ⏳ To be tested |
| NFR-1.4 | Support parallel processing with 4+ workers | 4-16 workers | ⏳ Phase 3 |
| NFR-1.5 | API response time p95 <2 seconds | <2s | ⏳ Phase 2 |

#### NFR-2: Reliability

| ID | Requirement | Target | Status |
|----|-------------|--------|--------|
| NFR-2.1 | System availability ≥99% | 99% | ⏳ Phase 4 |
| NFR-2.2 | Document processing failure rate <1% | <1% | ⏳ To be tested |
| NFR-2.3 | Graceful degradation on parser failure | Yes | ✅ Implemented |
| NFR-2.4 | Automatic retry on transient failures | Yes | ⏳ Phase 3 |
| NFR-2.5 | Error logging and monitoring | Yes | ⏳ Phase 3 |

#### NFR-3: Scalability

| ID | Requirement | Target | Status |
|----|-------------|--------|--------|
| NFR-3.1 | Horizontal scaling via worker processes | Yes | ⏳ Phase 3 |
| NFR-3.2 | Support for distributed task queue | Yes | ⏳ Phase 3 |
| NFR-3.3 | Handle documents up to 500MB | 500MB | ⏳ To be tested |
| NFR-3.4 | Support batch processing of 10,000+ docs | 10k+ | ⏳ Phase 3 |

#### NFR-4: Maintainability

| ID | Requirement | Target | Status |
|----|-------------|--------|--------|
| NFR-4.1 | Code test coverage ≥80% | ≥80% | ⏳ In progress |
| NFR-4.2 | Type hints on all public APIs | 100% | ✅ Implemented |
| NFR-4.3 | Comprehensive API documentation | Yes | ⏳ Phase 2 |
| NFR-4.4 | Modular architecture for extensibility | Yes | ✅ Implemented |
| NFR-4.5 | Response-Aware Development assumption tagging | Yes | ✅ Implemented |

#### NFR-5: Security

| ID | Requirement | Target | Status |
|----|-------------|--------|--------|
| NFR-5.1 | Input validation on all user inputs | Yes | ✅ Implemented |
| NFR-5.2 | No hardcoded credentials | Yes | ✅ Implemented |
| NFR-5.3 | Secure temporary file handling | Yes | ⏳ To be reviewed |
| NFR-5.4 | Rate limiting for web scraping | Yes | ✅ Configured |
| NFR-5.5 | Dependency vulnerability scanning | Yes | ⏳ Phase 1 |

#### NFR-6: Usability

| ID | Requirement | Target | Status |
|----|-------------|--------|--------|
| NFR-6.1 | Installation in <5 minutes | <5 min | ✅ Achieved |
| NFR-6.2 | Process first document in <10 minutes | <10 min | ✅ Achieved |
| NFR-6.3 | Clear error messages with remediation steps | Yes | ⏳ In progress |
| NFR-6.4 | Comprehensive user documentation | Yes | ⏳ Phase 2 |
| NFR-6.5 | Example code for common use cases | Yes | ✅ In README |

---

## Architecture Design

### System Context

```
┌─────────────────────────────────────────────────────────────────┐
│                        External Systems                          │
│  [File System] [S3 Storage] [Vector Databases] [PostgreSQL]     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Data Ingestor System                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ CLI Interface│  │  REST API    │  │  Python API  │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                  │                   │
│         └─────────────────┼──────────────────┘                   │
│                           ▼                                      │
│              ┌────────────────────────┐                          │
│              │   Document Router      │                          │
│              └────────────┬───────────┘                          │
│                           │                                      │
│         ┌─────────────────┼─────────────────┐                   │
│         ▼                 ▼                 ▼                    │
│   ┌──────────┐      ┌──────────┐      ┌──────────┐             │
│   │   PDF    │      │  DOCX    │      │   Web    │             │
│   │ Parsers  │      │ Parsers  │      │ Parsers  │             │
│   └────┬─────┘      └────┬─────┘      └────┬─────┘             │
│        │                 │                  │                    │
│        └─────────────────┼──────────────────┘                    │
│                          ▼                                       │
│              ┌───────────────────────┐                           │
│              │  Chunking Module      │                           │
│              └───────────┬───────────┘                           │
│                          ▼                                       │
│              ┌───────────────────────┐                           │
│              │  Quality Assessor     │                           │
│              └───────────┬───────────┘                           │
│                          ▼                                       │
│              ┌───────────────────────┐                           │
│              │  Storage Manager      │                           │
│              └───────────────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

### Component Specifications

#### 1. Document Router (✅ Implemented)

**Responsibility**: Route documents to appropriate parsers with fallback support

**Key Classes**:
- `DocumentRouter`: Main orchestrator
- `ParserRegistry`: Manages parser instances
- `FormatDetector`: Detects document formats

**Interfaces**:
```python
def process_document(
    source_path: str | Path | None,
    source_url: str | None,
    metadata: dict | None
) -> tuple[Document, ParserResult]
```

**Design Decisions**:
- Multi-stage format detection (libmagic → mimetypes → extension)
- Priority-based parser ordering
- Automatic fallback chain execution
- Hash-based deduplication cache

**Critical Assumptions**:
- `#CRITICAL`: At least one parser registered per supported format
- `#CRITICAL`: File may be deleted between validation and processing (race condition)
- `#ASSUME`: Hash-based deduplication sufficient for most use cases

#### 2. PDF Parsers (✅ Implemented)

**Implementations**:
- `PyMuPDFParser`: Reliable extraction with layout preservation
- `PyMuPDF4LLMParser`: LLM-optimized markdown generation

**Planned Additions** (Phase 2):
- `MarkerParser`: Advanced table and formula extraction
- `DoclingParser`: Enterprise-grade table structure
- `GROBIDParser`: Academic paper specialization

**Design Decisions**:
- Page-by-page processing to limit memory usage
- Font size heuristics for element classification
- Bounding box preservation for spatial context

**Critical Assumptions**:
- `#CRITICAL`: Large PDFs can exhaust memory (must process page-by-page)
- `#ASSUME`: Font size heuristics adequate for heading detection
- `#EDGE`: Password-protected PDFs require special handling

#### 3. Token Chunker (✅ Implemented)

**Responsibility**: Segment documents into token-aware chunks

**Algorithm**:
1. Separate tables from regular content
2. Chunk non-table elements with overlap
3. Split large elements at sentence boundaries
4. Add tables as standalone chunks
5. Add metadata and token counts

**Design Decisions**:
- Tiktoken for accurate token counting
- Configurable chunk size and overlap
- Table integrity preservation
- Context metadata in each chunk

**Critical Assumptions**:
- `#CRITICAL`: Token counting must match target LLM encoding
- `#CRITICAL`: Large elements may exceed chunk size (requires splitting)
- `#ASSUME`: Simple period split sufficient for sentence boundaries (should use proper tokenizer)

---

## Implementation Phases

### Phase 1: Foundation (Current - Week 1-3)

**Objective**: Core infrastructure with basic PDF support

**Completed**:
- [x] Core architecture (base classes, models, config)
- [x] Document router with format detection
- [x] Parser registry with fallback chains
- [x] PDF parsing (PyMuPDF + PyMuPDF4LLM)
- [x] Token-based chunking
- [x] CLI interface
- [x] Git repository with SSH signing
- [x] Project structure and documentation

**Next Steps**:
- [ ] Unit tests for core components (80% coverage)
- [ ] Integration tests for PDF processing
- [ ] Performance baseline measurements
- [ ] Security audit with Bandit
- [ ] Dependency vulnerability scan

**Exit Criteria**:
- Successfully process 100 sample PDFs
- 80% code coverage on core modules
- All linters passing (Black, Ruff, MyPy)
- Zero high-severity security issues

### Phase 2: Multi-Format Expansion (Week 4-6)

**Objective**: Add DOCX, Web, Video support

**Requirements**:
- [ ] FR-1.2: DOCX parser with python-docx
- [ ] FR-1.3: Web scraping with BeautifulSoup/Playwright
- [ ] FR-1.4: Video transcription with Faster-Whisper
- [ ] FR-1.6: Academic paper parser with GROBID
- [ ] FR-6.3: REST API with FastAPI
- [ ] FR-6.4: Batch processing API

**Deliverables**:
- DOCX parser with table extraction
- Web scraper with JavaScript rendering
- Video/audio transcription pipeline
- REST API with OpenAPI documentation
- Batch processing endpoint

**Exit Criteria**:
- Process all 4 format types successfully
- API documentation complete
- 80% coverage maintained
- Performance: 500+ docs/hour

### Phase 3: Quality & Scale (Week 7-9)

**Objective**: Production-ready quality and performance

**Requirements**:
- [ ] FR-3.4: Element-based chunking
- [ ] FR-4.1-4.5: Quality assessment module
- [ ] FR-5.1-5.3: Storage manager with PostgreSQL
- [ ] NFR-3.1-3.2: Celery task queue
- [ ] NFR-2.4: Retry logic and error handling
- [ ] NFR-1.4: Parallel processing

**Deliverables**:
- Element-aware chunking strategy
- Quality scoring system
- PostgreSQL metadata storage
- Celery worker configuration
- Monitoring and alerting
- Performance benchmarks

**Exit Criteria**:
- Process 1000+ docs/hour
- Quality scores >90% on test set
- <1% failure rate
- Horizontal scaling validated

### Phase 4: Production Deployment (Week 10-12)

**Objective**: Production-ready deployment

**Requirements**:
- [ ] FR-5.4-5.6: Vector store integrations
- [ ] NFR-5.5: S3 storage support
- [ ] NFR-2.1: 99% availability
- [ ] NFR-4.3: Complete documentation

**Deliverables**:
- Docker Compose orchestration
- Kubernetes manifests (optional)
- Vector store connectors (Pinecone, Weaviate, Qdrant)
- S3/MinIO integration
- Prometheus/Grafana monitoring
- Complete user guide and API docs
- Deployment runbooks

**Exit Criteria**:
- Production deployment successful
- Monitoring dashboards operational
- Documentation complete
- User acceptance testing passed

### Multimodal RAG Phase 1: Image Extraction (Week 13-14)

**Objective**: Enable extraction of images from PDFs as Base64-encoded data

**Based on**: Alejandro AO's 2025 Multimodal RAG Tutorial ([MULTIMODAL_RAG_COMPARISON.md](MULTIMODAL_RAG_COMPARISON.md))

**Requirements**:
- [ ] FR-10.1: Image extraction from PDFs as Base64
- [ ] FR-8.5: Base64 encoding for all PDF parsers
- [ ] Update PyMuPDFParser with `_extract_images()` method
- [ ] Update PyMuPDF4LLMParser for image handling
- [ ] Update MarkerParser for PIL Image to Base64 conversion
- [ ] Image metadata capture (size, format, position)

**Deliverables**:
- Enhanced PDF parsers with image extraction
- Unit tests for image extraction
- Integration tests with sample PDFs containing images
- Documentation for image handling

**Exit Criteria**:
- 100% of images extracted from test PDFs
- No memory issues with large PDFs (>100MB, 50+ images)
- Graceful error handling for corrupted images
- All three parsers support image extraction

**Estimated Effort**: 5 days (1 week)

### Multimodal RAG Phase 2: Summary-Based Embedding (Week 15-16)

**Objective**: Implement summary generation and embedding for improved retrieval

**Requirements**:
- [ ] FR-10.2-10.4: Summary generation for text, tables, images
- [ ] FR-10.5: Summary-based embedding architecture
- [ ] FR-8.7-8.8: LLM-based image descriptions and table summarization
- [ ] Parallel summarization chains (text LLM + vision LLM)
- [ ] Embedding module with sentence-transformers
- [ ] Summary caching for cost optimization

**Deliverables**:
- `src/data_ingestor/embeddings/` module
- `SummaryGenerator` class with multi-modal support
- `SummaryBasedEmbedder` class
- Configuration for LLM models (Haiku for text, Sonnet for vision)
- Unit and integration tests
- Performance benchmarks

**Exit Criteria**:
- Summary quality >8/10 (human evaluation)
- Summary generation <2s per chunk
- Vision LLM accurately describes images
- API costs reduced 80% with caching
- Embedding quality improved >15% vs. raw content

**Estimated Effort**: 10 days (2 weeks)

### Multimodal RAG Phase 3: Multi-Vector Store (Week 17-18)

**Objective**: Implement dual-store architecture for optimal retrieval

**Requirements**:
- [ ] FR-10.6: Multi-vector store architecture
- [ ] FR-10.7: Two-stage retrieval (summaries → originals)
- [ ] FR-5.4: Qdrant vector store integration
- [ ] Document store for original chunks (SQLite initially)
- [ ] Batch operations for 1000+ chunks
- [ ] Collection management (create, delete, update)

**Deliverables**:
- `src/data_ingestor/storage/` module
- `MultiVectorStore` class
- `DocumentStore` class (SQLite backend)
- Qdrant integration with collection management
- Configuration for Qdrant connection
- Integration tests with end-to-end storage/retrieval

**Exit Criteria**:
- Qdrant integration working with collection management
- Two-stage retrieval returns original content
- Batch operations handle 1000+ chunks efficiently
- Retrieval accuracy >85%
- Metadata preserved through storage/retrieval

**Estimated Effort**: 10 days (2 weeks)

### Multimodal RAG Phase 4: RAG Query Engine (Week 19-21)

**Objective**: Complete end-to-end multimodal RAG system

**Requirements**:
- [ ] FR-10.8-10.9: Multimodal LLM integration and RAG engine
- [ ] FR-10.10: Conversation memory
- [ ] FR-10.11: Source citation and provenance
- [ ] FR-10.12: Gradio demo interface
- [ ] Vision LLM integration (Claude 3.5 Sonnet)
- [ ] Query processing with multimodal content
- [ ] CLI query command
- [ ] Web interface for demos

**Deliverables**:
- `src/data_ingestor/rag/` module
- `MultimodalRAGChain` class
- `RAGResponse` model
- CLI `query` command
- Gradio demo interface
- Conversation memory implementation
- Source citation with page numbers
- End-to-end integration tests

**Exit Criteria**:
- Text-only queries work with high accuracy
- Image-based queries leverage vision LLM
- Table queries parse structure correctly
- Answer quality >8/10 (human evaluation)
- Response time <5s for typical queries
- Demo interface functional and user-friendly

**Estimated Effort**: 14 days (3 weeks)

### Phase 5: Advanced Features (Week 22+)

**Optional enhancements based on usage**:
- Speaker diarization for videos
- GraphRAG entity extraction
- Custom parser plugin system
- Web UI for management (beyond demo)
- Response streaming for better UX
- Advanced conversation memory with summarization
- Query optimization and caching

---

## Traceability Matrix

### Requirements → Implementation

| Requirement | Implementation | Test | Status |
|-------------|----------------|------|--------|
| FR-1.1 (PDF) | `PyMuPDFParser`, `PyMuPDF4LLMParser` | `test_pdf_parser.py` | ✅ Implemented |
| FR-2.1 (Format Detection) | `FormatDetector` | `test_format_detector.py` | ✅ Implemented |
| FR-2.2 (Parser Registry) | `ParserRegistry` | `test_parser_registry.py` | ✅ Implemented |
| FR-2.3 (Fallback) | `DocumentRouter.route_document()` | `test_router_fallback.py` | ✅ Implemented |
| FR-2.4 (Health Check) | `BaseParser.health_check()` | `test_parser_health.py` | ✅ Implemented |
| FR-3.1 (Token Chunking) | `TokenChunker` | `test_token_chunker.py` | ✅ Implemented |
| FR-3.2 (Overlap) | `TokenChunker._get_overlap()` | `test_chunk_overlap.py` | ✅ Implemented |
| FR-3.3 (Table Preservation) | `TokenChunker.preserve_tables` | `test_table_chunking.py` | ✅ Implemented |
| FR-5.3 (Deduplication) | `DocumentRouter.is_duplicate()` | `test_deduplication.py` | ✅ Implemented |
| FR-6.1 (CLI) | `cli/main.py` | `test_cli.py` | ✅ Implemented |

---

## Success Criteria

### Phase 1 Criteria (Current)

✅ **Technical**:
- [x] Process 100 sample PDFs successfully
- [ ] 80% code coverage
- [x] All linters passing
- [ ] Zero high-severity security issues

✅ **Functional**:
- [x] Extract text from PDFs with readable output
- [x] Generate chunks with proper token counts
- [x] CLI commands functional
- [x] Parser fallback working

### Overall Project Success Metrics

**Quality Metrics**:
- Text extraction accuracy: >90%
- Table structure accuracy: >85%
- Human evaluation score: >8/10

**Performance Metrics**:
- Throughput: ≥1000 docs/hour
- Processing time: <60s per document
- Failure rate: <1%

**Reliability Metrics**:
- System availability: ≥99%
- Successful fallback rate: >95%
- Error recovery rate: >90%

**Business Metrics**:
- Cost per document: <$0.01 at scale
- RAG retrieval improvement: 10-20%
- User satisfaction: ≥4.5/5

---

## Risk Management

### Technical Risks

| Risk | Impact | Probability | Mitigation | Owner |
|------|--------|-------------|------------|-------|
| Parser failures on edge cases | High | High | Implement fallback chains, comprehensive testing | Dev Team |
| Memory exhaustion on large files | High | Medium | Streaming/chunked processing, memory monitoring | Dev Team |
| GPL license conflicts | High | Low | Use MIT/Apache alternatives, legal review | Project Lead |
| GPU resource contention | Medium | Medium | CPU fallback, resource limits, queuing | DevOps |
| Performance degradation at scale | High | Medium | Load testing, profiling, optimization phase | Dev Team |

### Operational Risks

| Risk | Impact | Probability | Mitigation | Owner |
|------|--------|-------------|------------|-------|
| Infrastructure costs exceed budget | Medium | Medium | Auto-scaling policies, cost monitoring | DevOps |
| Key dependencies deprecated | Medium | Low | Dependency audits, abstraction layers | Dev Team |
| Security vulnerabilities | High | Low | Security scans, dependency updates | Security |
| Data loss | High | Low | Backup policies, redundancy | DevOps |

### Schedule Risks

| Risk | Impact | Probability | Mitigation | Owner |
|------|--------|-------------|------------|-------|
| Parser integration complexity | Medium | Medium | Early prototyping, extra time buffer | Dev Team |
| Scope creep | High | Medium | Strict phase boundaries, change control | Project Lead |
| Resource availability | Medium | Low | Cross-training, documentation | Team Lead |

---

## Testing Strategy

### Test Pyramid

```
        ╱╲
       ╱  ╲        E2E Tests (10%)
      ╱────╲       - Full pipeline integration
     ╱      ╲      - CLI command tests
    ╱────────╲
   ╱          ╲    Integration Tests (30%)
  ╱────────────╲   - Parser integration
 ╱              ╲  - API endpoint tests
╱────────────────╲ Unit Tests (60%)
                   - Core logic
                   - Individual components
```

### Test Categories

**Unit Tests (60%)** - Target: 80%+ coverage
- Core models and validation
- Parser implementations
- Chunking algorithms
- Format detection logic
- Configuration management

**Integration Tests (30%)**
- End-to-end document processing
- Parser fallback chains
- Database interactions
- API endpoints

**Performance Tests**
- Throughput benchmarks
- Memory profiling
- Concurrent processing
- Large file handling

**Quality Tests**
- Extraction accuracy evaluation
- Structure preservation validation
- Human evaluation sampling

**Security Tests**
- Input validation
- Dependency vulnerability scans
- Penetration testing (Phase 4)

### Test Data Sets

**PDF Test Set** (170 documents):
- 50 general PDFs (various layouts)
- 50 academic papers (arXiv, PubMed)
- 30 scanned documents
- 20 table-heavy documents
- 20 multi-language documents

**DOCX Test Set** (80 documents):
- 30 standard documents
- 20 table-heavy documents
- 20 complex formatting
- 10 with tracked changes

**Web Test Set** (100 sites):
- 50 static sites
- 30 JavaScript-heavy sites
- 20 complex layouts

**Video Test Set** (50 files):
- 20 lecture videos
- 10 podcast episodes
- 10 conference presentations
- 10 multi-speaker content

---

## Appendices

### A. Design Decisions Log

| Date | Decision | Rationale | Impact |
|------|----------|-----------|--------|
| 2025-11-02 | Use PyMuPDF over PDFMiner | Better performance, active maintenance | Faster PDF processing |
| 2025-11-02 | Implement parser fallback chains | Reliability and quality | Higher success rate |
| 2025-11-02 | Token-based chunking first | Simpler to implement, adequate for Phase 1 | Faster delivery |
| 2025-11-02 | Response-Aware Development | Risk mitigation, code quality | Better maintainability |
| 2025-11-03 | Adopt Alejandro AO's multimodal RAG patterns | Proven architecture, better retrieval quality | Comprehensive multimodal support |
| 2025-11-03 | Summary-based embedding over raw content | Improved retrieval accuracy (>15%), reduced storage | Better RAG performance |
| 2025-11-03 | Multi-vector store architecture | Optimal search and retrieval separation | Scalable retrieval system |
| 2025-11-03 | Claude 3.5 Sonnet for vision tasks | Superior multimodal capabilities, better quality | High-quality image understanding |
| 2025-11-03 | Qdrant for vector storage | Open-source, excellent performance, self-hostable | Cost-effective, production-ready |

### B. Technology Stack

**Core**:
- Python 3.11+
- Poetry for dependency management
- Pydantic for data validation

**Document Processing**:
- PyMuPDF (PDF parsing)
- python-docx (DOCX parsing)
- BeautifulSoup4 (Web scraping)
- Faster-Whisper (Transcription)

**Infrastructure**:
- FastAPI (REST API)
- Celery + Redis (Task queue)
- PostgreSQL (Metadata)
- Docker (Containerization)

**Multimodal RAG**:
- Qdrant (Vector store)
- sentence-transformers (Embeddings)
- Anthropic Claude 3.5 (Vision + Summarization)
- Gradio (Demo interface)

**Quality Assurance**:
- Pytest (Testing)
- Black, Ruff (Linting)
- MyPy (Type checking)
- Bandit (Security)

### C. Glossary

- **RAG**: Retrieval-Augmented Generation
- **Element**: A structural unit in a document (heading, paragraph, table, etc.)
- **Chunk**: A segmented portion of document content optimized for vector embedding
- **Parser**: A component that extracts structured data from a specific document format
- **Token**: A unit of text used by LLMs (approximately 4 characters)
- **Multimodal RAG**: RAG system that handles text, images, and tables together
- **Summary-Based Embedding**: Embedding summaries instead of raw content for improved retrieval
- **Multi-Vector Store**: Architecture with separate stores for summaries and original content
- **Vision LLM**: Language model with image understanding capabilities
- **Two-Stage Retrieval**: Search summaries, fetch originals

---

**Document Control**:
- **Version**: 2.0
- **Last Updated**: 2025-11-03
- **Next Review**: End of Multimodal Phase 1
- **Approval Status**: Updated with Multimodal RAG Roadmap

**Change Log**:
- 2025-11-02: Initial version created
- 2025-11-03: Added Multimodal RAG phases (FR-10) based on Alejandro AO's architecture
- 2025-11-03: Updated priorities for image extraction and summarization (FR-8.5, FR-8.7, FR-8.8)
- 2025-11-03: Added 4 new implementation phases for multimodal RAG (Weeks 13-21)
- 2025-11-03: Updated technology stack with Qdrant, Claude 3.5, Gradio
- 2025-11-03: Referenced new documentation: MULTIMODAL_RAG_COMPARISON.md and MULTIMODAL_RAG_ROADMAP.md
