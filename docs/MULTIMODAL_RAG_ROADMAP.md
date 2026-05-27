# Multimodal RAG Implementation Roadmap

**Document**: Implementation guide for multimodal RAG capabilities
**Date**: 2025-11-03
**Author**: Byron Williams
**Status**: Planning
**Based on**: Alejandro AO's 2025 Multimodal RAG Tutorial

---

## Executive Summary

This document provides a detailed implementation roadmap for adding multimodal RAG capabilities to the Data Ingestor system, based on Alejandro AO's proven architecture. The implementation is divided into four phases with clear milestones and acceptance criteria.

### Vision

Transform the Data Ingestor from a document ingestion pipeline into a **complete end-to-end multimodal RAG system** that can:
- Extract and understand images, tables, and text from documents
- Generate concise summaries for improved retrieval
- Enable semantic search across multimodal content
- Answer questions using vision-capable LLMs

---

## Table of Contents

1. [Phase Overview](#phase-overview)
2. [Phase 1: Image Extraction](#phase-1-image-extraction)
3. [Phase 2: Summary-Based Embedding](#phase-2-summary-based-embedding)
4. [Phase 3: Multi-Vector Store](#phase-3-multi-vector-store)
5. [Phase 4: Multimodal RAG Engine](#phase-4-multimodal-rag-engine)
6. [Testing Strategy](#testing-strategy)
7. [Deployment Guide](#deployment-guide)

---

## Phase Overview

### Timeline and Dependencies

```
Phase 1: Image Extraction (1 week)
   ↓
Phase 2: Summary-Based Embedding (2 weeks)
   ↓
Phase 3: Multi-Vector Store (2 weeks)
   ↓
Phase 4: Multimodal RAG Engine (2 weeks)
   ↓
Total: 7 weeks to complete multimodal RAG
```

### Resource Requirements

| Resource | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|----------|---------|---------|---------|---------|
| **Developer Time** | 1 week | 2 weeks | 2 weeks | 2 weeks |
| **LLM API Credits** | Minimal | $20-50 | $10-20 | $30-100 |
| **Qdrant Instance** | Not needed | Not needed | Required | Required |
| **Test Documents** | 50 PDFs with images | Same | Same | Same + queries |

---

## Phase 1: Image Extraction

### Objective

Enable extraction of images from PDFs as Base64-encoded data for multimodal processing.

### Requirements

| ID | Requirement | Priority | Dependencies |
|----|-------------|----------|--------------|
| IMG-1.1 | Extract images from PDF pages | P0 | PyMuPDF |
| IMG-1.2 | Store images as Base64 in elements | P0 | ElementType.IMAGE |
| IMG-1.3 | Capture image metadata (size, format, position) | P0 | ElementMetadata |
| IMG-1.4 | Handle image extraction failures gracefully | P0 | Error handling |
| IMG-1.5 | Support multiple image formats (JPEG, PNG, TIFF) | P1 | PyMuPDF codec support |

### Implementation

#### File Changes

**1. Update `src/data_ingestor/parsers/pdf_parser.py`**

Add image extraction method to all three parsers:

```python
class PyMuPDFParser(BaseParser):
    """Enhanced with image extraction."""

    def _extract_images(self, page: fitz.Page, page_num: int) -> list[DocumentElement]:
        """Extract images from PDF page as Base64.

        # #CRITICAL: Memory Management: Large images can exhaust memory
        # #VERIFY: Implement size limits and compression

        Args:
            page: PyMuPDF page object
            page_num: Page number (0-indexed)

        Returns:
            List of image elements with Base64 content
        """
        import base64

        elements = []
        image_list = page.get_images()

        for img_index, img_info in enumerate(image_list):
            try:
                xref = img_info[0]
                base_image = page.parent.extract_image(xref)

                # Convert to base64
                image_bytes = base_image["image"]
                image_base64 = base64.b64encode(image_bytes).decode()

                # Create data URI
                media_type = f"image/{base_image['ext']}"
                data_uri = f"data:{media_type};base64,{image_base64}"

                # Get bounding box (if available)
                bbox = img_info[1] if len(img_info) > 1 else None

                element = DocumentElement(
                    element_type=ElementType.IMAGE,
                    content=data_uri,
                    metadata=ElementMetadata(
                        page_number=page_num + 1,
                        coordinates=bbox,
                        extra={
                            "image_index": img_index,
                            "width": base_image["width"],
                            "height": base_image["height"],
                            "format": base_image["ext"],
                            "xref": xref,
                        }
                    )
                )
                elements.append(element)

            except Exception as e:
                logger.warning(
                    f"Failed to extract image {img_index} on page {page_num + 1}: {e}"
                )
                # Don't fail entire page extraction for one image
                continue

        return elements

    def parse(self, document: Document) -> ParserResult:
        """Enhanced parse method with image extraction."""
        # ... existing code ...

        for page_num in range(len(pdf_doc)):
            page = pdf_doc[page_num]

            # Extract text blocks (existing)
            text_elements = self._extract_text_blocks(page, page_num)
            elements.extend(text_elements)

            # Extract images (NEW)
            image_elements = self._extract_images(page, page_num)
            elements.extend(image_elements)

            # Update warning (replace existing warning)
            if image_elements:
                logger.info(
                    f"Page {page_num + 1}: Extracted {len(image_elements)} images"
                )

        # ... rest of existing code ...
```

**2. Update `MarkerParser` for Image Handling**

```python
class MarkerParser(BaseParser):
    """Enhanced with image Base64 conversion."""

    def parse(self, document: Document) -> ParserResult:
        """Parse with image extraction."""
        # ... existing marker extraction ...

        # Marker returns images dict: {image_id: PIL.Image}
        # Convert to Base64 elements
        for img_id, pil_image in images.items():
            import base64
            from io import BytesIO

            # Convert PIL Image to Base64
            buffer = BytesIO()
            pil_image.save(buffer, format="PNG")
            image_bytes = buffer.getvalue()
            image_base64 = base64.b64encode(image_bytes).decode()

            element = DocumentElement(
                element_type=ElementType.IMAGE,
                content=f"data:image/png;base64,{image_base64}",
                metadata=ElementMetadata(
                    extra={
                        "image_id": img_id,
                        "width": pil_image.width,
                        "height": pil_image.height,
                        "source": "marker",
                    }
                )
            )
            elements.append(element)

        # ... rest of code ...
```

#### Testing

**Test File**: `tests/unit/parsers/test_image_extraction.py`

```python
"""Tests for image extraction from PDFs."""

import pytest
from pathlib import Path

from data_ingestor.core.models import DocumentFormat, ElementType
from data_ingestor.parsers.pdf_parser import PyMuPDFParser
from data_ingestor.pipeline.router import DocumentRouter


class TestImageExtraction:
    """Test image extraction capabilities."""

    def test_extract_images_from_pdf(self):
        """Test basic image extraction."""
        parser = PyMuPDFParser()
        router = DocumentRouter()
        router.parser_registry.register(parser, [DocumentFormat.PDF])

        # Use test PDF with images
        document, result = router.process_document(
            source_path="tests/fixtures/sample_with_images.pdf"
        )

        # Verify images extracted
        images = [e for e in document.elements if e.element_type == ElementType.IMAGE]
        assert len(images) > 0, "Should extract at least one image"

    def test_image_base64_format(self):
        """Test Base64 encoding format."""
        # ... test that images are properly Base64 encoded ...

    def test_image_metadata(self):
        """Test image metadata capture."""
        # ... test width, height, format captured ...

    def test_image_extraction_failure_handling(self):
        """Test graceful handling of extraction failures."""
        # ... test error handling ...
```

#### Acceptance Criteria

- [ ] Images extracted from at least 3 test PDFs
- [ ] Base64 encoding validated for all supported formats
- [ ] Metadata captured (size, format, page number)
- [ ] No failures on PDFs without images
- [ ] Graceful handling of corrupted images
- [ ] Memory usage acceptable (<500MB for 100MB PDF with 50 images)

### Estimated Effort

- **Development**: 3 days
- **Testing**: 1 day
- **Documentation**: 1 day
- **Total**: 5 days (1 week)

---

## Phase 2: Summary-Based Embedding

### Objective

Implement summary generation and embedding for all content types (text, tables, images) to improve retrieval quality.

### Requirements

| ID | Requirement | Priority | Dependencies |
|----|-------------|----------|--------------|
| SUM-2.1 | Generate text summaries using LLM | P0 | Anthropic API |
| SUM-2.2 | Generate table summaries with structure description | P0 | Anthropic API |
| SUM-2.3 | Generate image descriptions using vision LLM | P0 | Anthropic Claude 3.5 Sonnet |
| SUM-2.4 | Parallel processing of different content types | P1 | asyncio |
| SUM-2.5 | Embed summaries instead of raw content | P0 | sentence-transformers |
| SUM-2.6 | Cache summaries to avoid regeneration | P1 | Redis or SQLite |

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Chunk Input                                │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              Content Type Detection                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │   Text     │  │   Table    │  │   Image    │                │
│  └─────┬──────┘  └──────┬─────┘  └──────┬─────┘                │
└────────┼─────────────────┼────────────────┼──────────────────────┘
         │                 │                │
         ▼                 ▼                ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│  Fast LLM      │  │  Fast LLM      │  │  Vision LLM    │
│  (Haiku)       │  │  (Haiku)       │  │  (Sonnet 3.5)  │
│  Summarize     │  │  Describe      │  │  Describe      │
│  Key Concepts  │  │  Structure     │  │  Content       │
└────────┬───────┘  └────────┬───────┘  └────────┬───────┘
         │                   │                    │
         └───────────────────┼────────────────────┘
                             ▼
                    ┌────────────────┐
                    │  Embed Summary │
                    │ (SentenceT5)   │
                    └────────┬───────┘
                             │
                             ▼
                 ┌───────────────────────┐
                 │ Return: (summary,     │
                 │ embedding, original)  │
                 └───────────────────────┘
```

### Implementation

#### New Module: `src/data_ingestor/embeddings/`

**File: `src/data_ingestor/embeddings/__init__.py`**
```python
"""Embedding module for multimodal content."""

from .summary_embedder import SummaryBasedEmbedder, SummaryGenerator

__all__ = ["SummaryBasedEmbedder", "SummaryGenerator"]
```

**File: `src/data_ingestor/embeddings/summary_embedder.py`**

Full implementation in docs/code_examples/summary_embedder.py (see below).

#### Configuration

**Update `src/data_ingestor/core/config.py`:**

```python
class Settings(BaseSettings):
    """Enhanced settings with embedding configuration."""

    # ... existing settings ...

    # Embedding configuration
    embedding_model: str = "all-MiniLM-L6-v2"  # SentenceTransformer model
    summary_max_length: int = 200  # Max tokens for summaries
    use_summary_embeddings: bool = True  # Enable summary-based embedding

    # LLM configuration for summarization
    summarization_model: str = "claude-3-5-haiku-20241022"  # Fast, cheap
    vision_model: str = "claude-3-5-sonnet-20241022"  # Vision capable

    # Caching
    enable_summary_cache: bool = True
    summary_cache_ttl: int = 86400  # 24 hours
```

#### Testing

**Test File**: `tests/unit/embeddings/test_summary_embedder.py`

```python
"""Tests for summary-based embedding."""

import pytest
from data_ingestor.embeddings.summary_embedder import (
    SummaryGenerator,
    SummaryBasedEmbedder
)
from data_ingestor.core.models import Chunk, DocumentElement, ElementType


class TestSummaryGeneration:
    """Test summary generation for different content types."""

    @pytest.mark.asyncio
    async def test_text_summarization(self):
        """Test text content summarization."""
        generator = SummaryGenerator()
        text = "Long text about quarterly revenue..." * 100

        summary = await generator.summarize_text(text)

        assert len(summary) < len(text)
        assert "revenue" in summary.lower()

    @pytest.mark.asyncio
    async def test_table_summarization(self):
        """Test table description generation."""
        # ... test table summarization ...

    @pytest.mark.asyncio
    async def test_image_description(self):
        """Test image description with vision LLM."""
        # ... test with sample image ...


class TestSummaryBasedEmbedder:
    """Test complete summary-based embedding pipeline."""

    @pytest.mark.asyncio
    async def test_embed_text_chunk(self):
        """Test embedding text chunk via summary."""
        # ... test end-to-end embedding ...

    @pytest.mark.asyncio
    async def test_parallel_processing(self):
        """Test parallel summarization of multiple chunks."""
        # ... test async processing ...
```

#### Acceptance Criteria

- [ ] Text summaries generated in <2 seconds per chunk
- [ ] Table descriptions capture structure and key data
- [ ] Image descriptions identify main visual elements
- [ ] Embeddings are 384-dimensional (sentence-transformers default)
- [ ] Parallel processing works for 100+ chunks
- [ ] Summary cache reduces API costs by >80% on repeated processing

### Estimated Effort

- **Development**: 5 days
- **Testing**: 3 days
- **Integration**: 2 days
- **Total**: 10 days (2 weeks)

---

## Phase 3: Multi-Vector Store

### Objective

Implement dual-store architecture: vector store for summary embeddings, document store for original content.

### Requirements

| ID | Requirement | Priority | Dependencies |
|----|-------------|----------|--------------|
| MVS-3.1 | Integrate with Qdrant for vector storage | P0 | Qdrant server |
| MVS-3.2 | Implement document store for originals | P0 | SQLite or PostgreSQL |
| MVS-3.3 | Link summaries to originals via chunk_id | P0 | - |
| MVS-3.4 | Two-stage retrieval (search summaries, fetch originals) | P0 | - |
| MVS-3.5 | Support batch storage operations | P1 | - |
| MVS-3.6 | Collection management (create, delete, update) | P1 | - |

### Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    Store Chunk with Summary                     │
│  Input: (chunk, summary, embedding)                            │
└──────────────────────────┬─────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                                    ▼
┌──────────────────────┐          ┌──────────────────────────┐
│  Qdrant Vector Store │          │   Document Store         │
│  ┌────────────────┐  │          │  ┌─────────────────────┐ │
│  │ chunk_id       │  │          │  │ chunk_id (key)      │ │
│  │ embedding      │  │◄────────►│  │ original_chunk      │ │
│  │ summary        │  │ link by  │  │ elements            │ │
│  │ metadata       │  │ chunk_id │  │ metadata            │ │
│  └────────────────┘  │          │  └─────────────────────┘ │
└──────────────────────┘          └──────────────────────────┘
         │                                    │
         └─────────────────┬──────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────┐
│                    Retrieval Flow                               │
│                                                                 │
│  1. Query arrives                                              │
│  2. Embed query                                                │
│  3. Search Qdrant (summary embeddings) → get chunk_ids         │
│  4. Fetch originals from Document Store                        │
│  5. Return original chunks (not summaries!)                    │
└────────────────────────────────────────────────────────────────┘
```

### Implementation

#### New Module: `src/data_ingestor/storage/`

**File: `src/data_ingestor/storage/__init__.py`**
```python
"""Storage module for multi-vector architecture."""

from .multi_vector_store import MultiVectorStore, DocumentStore

__all__ = ["MultiVectorStore", "DocumentStore"]
```

**File: `src/data_ingestor/storage/multi_vector_store.py`**

Full implementation provided in comparison document.

#### Configuration

**Update `src/data_ingestor/core/config.py`:**

```python
class Settings(BaseSettings):
    """Enhanced with vector store configuration."""

    # ... existing settings ...

    # Qdrant configuration
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "documents"
    qdrant_api_key: str | None = None

    # Document store configuration
    docstore_type: str = "sqlite"  # sqlite, postgres, memory
    docstore_path: str = "data/docstore.db"  # For SQLite
    docstore_url: str | None = None  # For PostgreSQL

    # Retrieval configuration
    default_retrieval_k: int = 5
    max_retrieval_k: int = 20
```

#### Testing

**Test File**: `tests/integration/test_multi_vector_store.py`

```python
"""Integration tests for multi-vector store."""

import pytest
from data_ingestor.storage.multi_vector_store import MultiVectorStore
from data_ingestor.embeddings.summary_embedder import SummaryBasedEmbedder


class TestMultiVectorStore:
    """Test multi-vector store architecture."""

    @pytest.fixture
    def store(self):
        """Create test store."""
        return MultiVectorStore(
            qdrant_url="http://localhost:6333",
            collection_name="test_collection",
            embedding_dim=384,
        )

    def test_store_and_retrieve(self, store):
        """Test complete store and retrieval flow."""
        # ... test storing chunks with summaries ...
        # ... test retrieval returns originals ...

    def test_summary_search_original_retrieval(self, store):
        """Test that search happens on summaries but retrieval returns originals."""
        # ... verify two-stage retrieval ...

    def test_batch_storage(self, store):
        """Test batch storage operations."""
        # ... test storing 1000+ chunks efficiently ...
```

#### Acceptance Criteria

- [ ] Qdrant integration working with collection management
- [ ] Document store implemented (SQLite initially)
- [ ] Chunk IDs correctly link summaries to originals
- [ ] Retrieval returns original content, not summaries
- [ ] Batch operations handle 1000+ chunks efficiently
- [ ] Metadata preserved through storage and retrieval

### Estimated Effort

- **Development**: 6 days
- **Testing**: 3 days
- **Integration**: 1 day
- **Total**: 10 days (2 weeks)

---

## Phase 4: Multimodal RAG Engine

### Objective

Implement end-to-end RAG query engine with multimodal LLM support (images + text + tables).

### Requirements

| ID | Requirement | Priority | Dependencies |
|----|-------------|----------|--------------|
| RAG-4.1 | Query processing with embedding | P0 | MultiVectorStore |
| RAG-4.2 | Multimodal content separation (images/tables/text) | P0 | - |
| RAG-4.3 | Vision LLM integration (Claude 3.5 Sonnet) | P0 | Anthropic API |
| RAG-4.4 | Prompt construction with images and text | P0 | - |
| RAG-4.5 | Source citation and provenance tracking | P1 | - |
| RAG-4.6 | Conversation memory for multi-turn dialogues | P1 | - |
| RAG-4.7 | Response streaming for better UX | P2 | - |

### Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                      User Question                              │
└──────────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────┐
│                  1. Embed Question                              │
└──────────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────┐
│         2. Retrieve Relevant Chunks (via MultiVectorStore)      │
│            → Search summaries, return originals                 │
└──────────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────┐
│         3. Separate Content by Modality                         │
│  ┌───────────┐  ┌───────────────┐  ┌──────────────────┐      │
│  │  Images   │  │  Tables       │  │  Text            │      │
│  │  (Base64) │  │  (Markdown)   │  │  (Paragraphs)    │      │
│  └─────┬─────┘  └───────┬───────┘  └────────┬─────────┘      │
└────────┼─────────────────┼──────────────────┼─────────────────┘
         │                 │                  │
         └─────────────────┼──────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────┐
│         4. Construct Multimodal Prompt                          │
│                                                                 │
│  [Text Context] + [Table Context] + [Image 1] + [Image 2] ...  │
│  + [Question]                                                   │
└──────────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────┐
│         5. Query Vision-Capable LLM                             │
│            (Claude 3.5 Sonnet)                                  │
└──────────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────┐
│         6. Return RAGResponse                                   │
│            - Answer text                                        │
│            - Source chunks                                      │
│            - Modalities used                                    │
│            - Metadata (model, cost, etc.)                       │
└────────────────────────────────────────────────────────────────┘
```

### Implementation

#### New Module: `src/data_ingestor/rag/`

**File: `src/data_ingestor/rag/__init__.py`**
```python
"""RAG module for multimodal question answering."""

from .query_engine import MultimodalRAGChain, RAGResponse

__all__ = ["MultimodalRAGChain", "RAGResponse"]
```

**File: `src/data_ingestor/rag/query_engine.py`**

Full implementation provided in comparison document.

#### CLI Integration

**Update `src/data_ingestor/cli/main.py`:**

```python
@cli.command()
@click.argument("question")
@click.option("--collection", default="documents", help="Qdrant collection name")
@click.option("--k", default=5, help="Number of chunks to retrieve")
@click.option("--model", default="claude-3-5-sonnet-20241022", help="LLM model")
def query(question: str, collection: str, k: int, model: str):
    """Query documents with multimodal RAG."""
    from data_ingestor.rag.query_engine import MultimodalRAGChain
    from data_ingestor.storage.multi_vector_store import MultiVectorStore
    from anthropic import Anthropic

    # Initialize components
    store = MultiVectorStore(
        qdrant_url=settings.qdrant_url,
        collection_name=collection,
        embedding_dim=384,
    )

    rag_chain = MultimodalRAGChain(
        retriever=store,
        anthropic_client=Anthropic(),
        model=model,
    )

    # Embed question
    from sentence_transformers import SentenceTransformer
    embedder = SentenceTransformer(settings.embedding_model)
    question_embedding = embedder.encode(question)

    # Query
    response = asyncio.run(rag_chain.query(question, question_embedding, k=k))

    # Display results
    click.echo(f"\n{response.answer}\n")
    click.echo(f"Modalities used: {', '.join(response.modalities_used)}")
    click.echo(f"Sources: {len(response.sources)} chunks")
```

#### Testing

**Test File**: `tests/integration/test_multimodal_rag.py`

```python
"""Integration tests for multimodal RAG."""

import pytest
from data_ingestor.rag.query_engine import MultimodalRAGChain


class TestMultimodalRAG:
    """Test end-to-end multimodal RAG."""

    @pytest.mark.asyncio
    async def test_text_only_query(self):
        """Test query with text-only results."""
        # ... test retrieval and generation ...

    @pytest.mark.asyncio
    async def test_image_query(self):
        """Test query that retrieves and uses images."""
        # ... test vision capabilities ...

    @pytest.mark.asyncio
    async def test_table_query(self):
        """Test query involving table data."""
        # ... test table understanding ...

    @pytest.mark.asyncio
    async def test_multimodal_query(self):
        """Test query using images + tables + text."""
        # ... test complete multimodal workflow ...
```

#### Acceptance Criteria

- [ ] Text-only queries work with high accuracy
- [ ] Image-based queries leverage vision LLM
- [ ] Table queries parse structure correctly
- [ ] Mixed queries use all relevant modalities
- [ ] Source citation includes page numbers and chunk IDs
- [ ] Response time <5 seconds for typical queries
- [ ] Conversation memory maintains context across turns

### Estimated Effort

- **Development**: 7 days
- **Testing**: 4 days
- **Documentation**: 3 days
- **Total**: 14 days (2 weeks+)

---

## Testing Strategy

### Unit Tests

**Coverage Target**: 80%+

- Summary generation for each content type
- Embedding generation
- Vector store operations
- Document store CRUD operations
- Query processing logic

### Integration Tests

**Scenarios**:
1. End-to-end document processing with summaries
2. Store and retrieve with multi-vector architecture
3. Complete RAG query with multimodal content
4. Batch processing of 100+ documents
5. Concurrent queries

### Performance Tests

**Metrics**:
- Summary generation: <2s per chunk
- Embedding generation: <1s per batch of 32
- Retrieval: <500ms for k=10
- Complete RAG query: <5s
- Batch processing: 1000+ docs/hour

### Quality Tests

**Evaluation**:
- Retrieval accuracy: >85% on test queries
- Answer quality: Human evaluation >8/10
- Image understanding: Correct descriptions >90%
- Table understanding: Structure preserved >85%

---

## Deployment Guide

### Infrastructure Requirements

**Minimum**:
- 4 CPU cores
- 8GB RAM
- 50GB storage
- Qdrant instance

**Recommended**:
- 8 CPU cores
- 16GB RAM
- 200GB SSD storage
- Dedicated Qdrant cluster

### Configuration

**Environment Variables**:
```bash
# LLM API
ANTHROPIC_API_KEY=sk-...

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=...

# Embedding
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Performance
MAX_CONCURRENT_SUMMARIES=10
SUMMARY_CACHE_ENABLED=true
```

### Deployment Steps

1. **Deploy Qdrant**:
   ```bash
   docker run -p 6333:6333 qdrant/qdrant
   ```

2. **Install Dependencies**:
   ```bash
   uv sync --extra advanced-pdf,ml
   ```

3. **Initialize Database**:
   ```bash
   uv run data-ingestor init --create-collections
   ```

4. **Process Documents**:
   ```bash
   uv run data-ingestor process-batch docs/ --with-summaries
   ```

5. **Start Query Interface**:
   ```bash
   uv run data-ingestor serve --port 8000
   ```

---

## Success Criteria

### Phase 1 (Image Extraction)
- [ ] 100% of images extracted from test PDFs
- [ ] No memory issues with large PDFs
- [ ] Graceful error handling

### Phase 2 (Summary-Based Embedding)
- [ ] Summary quality >8/10 (human evaluation)
- [ ] Embedding generation <1s per batch
- [ ] API costs reduced by 80% with caching

### Phase 3 (Multi-Vector Store)
- [ ] Retrieval accuracy >85%
- [ ] Two-stage retrieval working correctly
- [ ] Batch operations efficient

### Phase 4 (Multimodal RAG)
- [ ] Answer quality >8/10
- [ ] Image questions answered correctly
- [ ] Response time <5s
- [ ] Source citations accurate

---

**Document Control**:
- **Version**: 1.0
- **Last Updated**: 2025-11-03
- **Next Review**: After Phase 1 completion
- **Status**: Planning
