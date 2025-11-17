# ADR-0003: Hybrid Deployment Model

**Status**: Accepted
**Date**: 2025-11-17
**Deciders**: Claude Code, Project Lead
**Technical Story**: Sprint 0.1 - Deployment Strategy Decision (Q7 Resolution)

## Context and Problem Statement

Project B (Layout, OCR & Structural Extraction Engine) must integrate with Projects A, C, and D in the RAG pipeline. The integration architecture significantly impacts latency, scalability, and operational complexity. Should Project B be invoked in-process as a Python library, deployed as a REST API service, coordinated via message queue, or use a hybrid approach?

The pipeline requires <5ms latency for single-document processing (real-time use cases) while also supporting batch processing of large document collections (10,000+ documents). The chosen deployment model must balance latency, scalability, and operational complexity.

## Decision Drivers

* **Latency Requirements**: <5ms integration overhead for single-document processing (real-time use cases)
* **Batch Scalability**: Support parallel processing of 10,000+ documents for batch ingestion
* **Serialization Overhead**: JSON serialization adds ~200μs per document (non-trivial at scale)
* **Network Overhead**: HTTP requests add 1-5ms latency even on localhost
* **Operational Simplicity**: Prefer simpler deployment for single-system integration
* **Future Flexibility**: Enable distributed deployment if scaling needs change
* **Resource Isolation**: Prevent OCR workloads from impacting other pipeline components
* **Development Velocity**: Minimize infrastructure complexity during active development

## Considered Options

* **Option 1: Hybrid Approach** - In-process primary path + optional Redis queue for batch processing
* **Option 2: Pure In-Process** - Always use direct Python function calls (no serialization)
* **Option 3: Pure REST API** - Deploy as FastAPI service with HTTP communication
* **Option 4: Pure Message Queue** - Coordinate all processing via Redis/RabbitMQ

## Decision Outcome

**Chosen option**: "Option 1: Hybrid Approach", because it provides <5ms latency for real-time single-document processing (in-process) while enabling future scalability for batch workloads (optional Redis queue). This approach optimizes for the common case (single-system integration) while preserving flexibility for distributed deployment.

### Implementation Details

1. **Primary Path (In-Process)**:
   ```python
   from project_b import process_document

   # Project A calls Project B directly (zero serialization overhead)
   metadata = DocumentMetadata(...)  # Pydantic model
   ocr_doc = process_document(metadata)  # Returns OCRDocument model
   ```

2. **Optional Batch Path (Redis Queue)**:
   ```python
   from project_b.queue import submit_batch

   # Submit batch for async processing
   job_ids = submit_batch(metadata_list, output_gcs_path)

   # Poll for completion or register callback
   results = await_batch_completion(job_ids)
   ```

3. **Configuration**:
   - Environment variable: `PROJECT_B_MODE=in-process|queue` (default: `in-process`)
   - Queue config: `REDIS_URL`, `BATCH_WORKER_COUNT`, `MAX_QUEUE_SIZE`

4. **Deployment Scenarios**:
   - **Single-System**: Projects A→B→C→D in single process (in-process mode)
   - **Batch Processing**: Redis queue with distributed workers (queue mode)
   - **Hybrid**: Real-time documents via in-process, batch via queue (both modes)

### Positive Consequences

* **Optimal Latency**: In-process path achieves <5ms integration overhead (zero serialization)
* **Zero Network Overhead**: No HTTP/RPC layer for primary use case
* **Future Scalability**: Queue path enables horizontal scaling if needed
* **Operational Simplicity**: Single-system deployment requires no infrastructure (no Redis, no API server)
* **Development Velocity**: No FastAPI/REST API overhead during active development
* **Resource Isolation**: Queue workers can run on separate machines with GPU isolation
* **Flexible Deployment**: Can switch modes via configuration without code changes

### Negative Consequences

* **Dual Code Paths**: Must maintain both in-process and queue execution paths
* **Testing Complexity**: Must test both deployment modes to ensure consistency
* **Queue Infrastructure**: Batch mode requires Redis deployment and monitoring
* **Serialization Logic**: Queue path requires JSON serialization (DocumentMetadata → JSON → DocumentMetadata)
* **Documentation Burden**: Must document both deployment modes clearly

## Pros and Cons of the Options

### Option 1: Hybrid Approach (In-Process + Queue)

**Pros:**
* Good, because it optimizes for common case (single-system, <5ms latency) while preserving scalability
* Good, because zero serialization overhead for in-process path
* Good, because queue path enables horizontal scaling for batch workloads
* Good, because it can be deployed as single-system initially (no infrastructure)
* Good, because it enables resource isolation (GPU workers) when needed
* Good, because configuration-driven mode switching (no code changes)

**Cons:**
* Bad, because it requires maintaining two execution paths (in-process + queue)
* Bad, because testing must cover both modes to ensure consistency
* Bad, because queue infrastructure (Redis) adds operational complexity for batch mode
* Bad, because serialization logic must be implemented for queue path

### Option 2: Pure In-Process

**Pros:**
* Good, because it provides absolute minimal latency (<5ms integration overhead)
* Good, because zero serialization overhead (Pydantic models passed directly)
* Good, because simplest possible deployment (no infrastructure required)
* Good, because easiest to develop and test (no distributed system complexity)
* Good, because no network overhead or failure modes

**Cons:**
* Bad, because it couples all 4 projects into single process (scaling limitations)
* Bad, because OCR workloads can impact other pipeline components (resource contention)
* Bad, because batch processing of 10,000+ documents may exhaust memory
* Bad, because no resource isolation (GPU contention if multiple projects use GPU)
* Bad, because future migration to distributed deployment requires significant refactoring

### Option 3: Pure REST API

**Pros:**
* Good, because it provides clear service boundaries (microservices architecture)
* Good, because it enables independent scaling and deployment of each project
* Good, because resource isolation prevents OCR workloads from impacting other services
* Good, because language-agnostic integration (non-Python projects can call API)
* Good, because monitoring and observability are well-understood (HTTP metrics, tracing)

**Cons:**
* Bad, because HTTP overhead adds 1-5ms latency per request (fails <5ms requirement)
* Bad, because JSON serialization adds ~200μs overhead per document
* Bad, because it requires API server deployment and management (FastAPI, gunicorn, nginx)
* Bad, because network failures introduce new failure modes (timeouts, retries)
* Bad, because local development requires running multiple services (Docker Compose complexity)
* Bad, because it adds unnecessary complexity for single-system deployments

### Option 4: Pure Message Queue

**Pros:**
* Good, because it provides excellent scalability (horizontal scaling via workers)
* Good, because decoupling via async messaging (producers and consumers independent)
* Good, because natural batch processing support (queue buffers documents)
* Good, because resource isolation via separate worker processes

**Cons:**
* Bad, because it adds significant latency (queue latency + serialization overhead: 5-20ms)
* Bad, because it requires message broker infrastructure (Redis/RabbitMQ deployment)
* Bad, because it introduces operational complexity (monitoring queues, dead letters, retries)
* Bad, because async-only processing complicates synchronous use cases (polling/callbacks)
* Bad, because serialization overhead for every document (no in-process optimization)
* Bad, because overkill for single-system deployments (adds complexity without benefit)

## Links

* [Related to] [ADR-0001: Clean Slate Migration Strategy](ADR-0001-clean-slate-migration.md) - Clean slate enables flexible deployment model
* [Related to] [ADR-0002: Pydantic v2 for Schema Validation](ADR-0002-pydantic-v2-schema-validation.md) - Efficient serialization critical for queue path
* [References] Legacy deployment: Single-process CLI tool (`data-ingestor process`)
* [References] Future consideration: Kubernetes deployment with Celery workers

---

## Notes

**Latency Breakdown (Single Document)**:

| Component | In-Process | Queue | REST API |
|-----------|-----------|-------|----------|
| Serialization | 0μs | 200μs | 200μs |
| Network | 0μs | 100μs | 1-5ms |
| Queue overhead | 0μs | 500μs | 0μs |
| **Total overhead** | **0μs** | **800μs** | **1.4-5.2ms** |
| OCR time (typical) | 40-400ms | 40-400ms | 40-400ms |
| **Total time** | **40-400ms** | **41-401ms** | **41-405ms** |

**Batch Processing (10,000 Documents)**:

| Metric | In-Process (Sequential) | Queue (8 Workers) | REST API (8 Workers) |
|--------|------------------------|-------------------|---------------------|
| Serialization | 0s | 2s | 2s |
| OCR time | 6,667s (1.85h) | 833s (13.9m) | 833s (13.9m) |
| Total time | 6,667s | 835s | 835s |
| Throughput | 1.5 docs/s | 12 docs/s | 12 docs/s |

**Deployment Scenarios**:

1. **Development** (In-Process):
   - Single Python process for all 4 projects
   - pytest integration tests run entire pipeline in-process
   - No infrastructure required

2. **Production - Small Scale** (In-Process):
   - Single server with GPU (RTX 4090, A100)
   - Projects A→B→C→D in single process
   - 1-10 docs/hour, <5ms integration latency

3. **Production - Large Scale** (Queue):
   - Redis queue with 8-16 GPU workers
   - Horizontal scaling for batch processing
   - 100-1,000 docs/hour, ~1ms queue overhead

4. **Production - Mixed** (Hybrid):
   - Real-time documents via in-process (<5ms)
   - Batch ingestion via queue (scalable)
   - Best of both worlds for production systems

**Future Consideration**: If Projects A, C, D are implemented in different languages (e.g., Rust, Go), REST API becomes necessary. Hybrid approach enables future migration to REST API without major refactoring.
