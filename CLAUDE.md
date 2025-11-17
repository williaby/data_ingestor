# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Reference**: Global standards apply from `~/.claude/CLAUDE.md`. Only project-specific configurations documented below.

## Claude Code Supervisor Role (CRITICAL)

**Claude Code acts as the SUPERVISOR for all development tasks and MUST:**

1. **Always Use TodoWrite Tool**: Create and maintain TODO lists for ALL tasks to track progress
2. **Assign Tasks to Agents**: Each TODO item should be assigned to a specialized agent via MCP Server
3. **Review Agent Work**: Validate all agent outputs before proceeding to next steps
4. **Use Temporary Reference Files**: Create `.tmp-` prefixed files in `tmp_cleanup/` folder to store detailed context that might be lost during compaction
5. **Maintain Continuity**: Use reference files to preserve TODO details across conversation compactions

### Agent Assignment Patterns

```bash
# Always assign TODO items to appropriate agents:
- Parser implementation → Code Review Agent (via mcp__zen__codereview)
- Benchmarking tasks → Analysis Agent (via mcp__zen__analyze)
- Security tasks → Security Agent (via mcp__zen__secaudit)
- Testing → Test Engineer Agent (via mcp__zen__testgen)
- Documentation → Documentation Agent (via mcp__zen__docgen)
- Debugging → Debug Agent (via mcp__zen__debug)
- Refactoring → Refactor Agent (via mcp__zen__refactor)
```

### Temporary Reference Files (Anti-Compaction Strategy)

**ALWAYS create temporary reference files when:**
- TODO list contains >5 items
- Complex implementation details need preservation
- Multi-step workflows span multiple conversation turns (e.g., benchmarking, evaluation)
- Agent assignments and progress need tracking

**Naming Convention**: `tmp_cleanup/.tmp-{task-type}-{timestamp}.md`

**Examples**:
- `tmp_cleanup/.tmp-phase1b-baseline-20251105.md`
- `tmp_cleanup/.tmp-intelligent-ocr-implementation-20251105.md`
- `tmp_cleanup/.tmp-docling-integration-20251105.md`

### Supervisor Workflow Patterns (MANDATORY)

**Every development task MUST follow this pattern:**

1. **Create TODO List**: Use TodoWrite tool to break down the task into specific, actionable items
2. **Agent Assignment**: Assign each TODO item to the most appropriate specialized agent
3. **Progress Tracking**: Mark items as in_progress when assigned, completed when validated
4. **Reference File Creation**: For complex tasks, create `.tmp-` reference files immediately
5. **Agent Output Validation**: Review all agent work before marking items complete

**For complex tasks requiring multiple agents:**

1. **Sequential Dependencies**: Use TodoWrite to show dependencies between tasks
2. **Parallel Execution**: Assign independent tasks to multiple agents simultaneously
3. **Integration Points**: Create specific TODO items for integrating agent outputs
4. **Quality Gates**: Assign review tasks to appropriate agents after implementation

## Project Overview

**Data Ingestor** is a production-grade RAG data ingestion pipeline that transforms diverse document formats (PDF, DOCX, HTML, Video, Audio) into high-quality, structured data through intelligent routing, adaptive OCR, and comprehensive format support.

**Current Phase**: Phase 1b - Performance Benchmarking & Baseline Establishment (see [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md))

**Key Differentiators**:
- Intelligent OCR routing (~5x average speedup vs blanket OCR - Phase 2)
- Hybrid parser architecture (Marker GPL-3.0 + Docling MIT)
- 97.9% table accuracy with Docling TableFormer (Phase 2)
- Comprehensive evaluation framework with DocLayNet (81,471 documents)

## Development Workflow

> **Reference**: Global git workflow applies. Project-specific steps below.

**Before Changes:**
1. `poetry install --sync`
2. `make lint` (verify code quality baseline)
3. `make test-fast` (verify tests passing)

**During Development:**
1. Write tests first (TDD encouraged)
2. Implement feature with assumption tagging (#CRITICAL, #ASSUME, #EDGE)
3. Run `make test-fast` frequently during development
4. Tag assumptions using Response-Aware Development (RAD) framework

**Before Commit:**
1. `make test-pre-commit` (< 2 min validation)
2. `make lint` (Black, Ruff, MyPy, markdownlint, yamllint)
3. `make security` (Bandit, Safety dependency scan)
4. Pre-commit hooks execute automatically

**Before PR:**
1. `make test-pr` (< 5 min full validation)
2. Ensure 80%+ coverage maintained
3. Update documentation if needed
4. Use `/verify-assumptions-smart` for assumption verification
5. Use global PR preparation workflow from `~/.claude/CLAUDE.md`

## Architecture Decision Records (ADRs)

**All significant architectural decisions must be documented as ADRs before implementation.**

### What are ADRs?

Architecture Decision Records document the context, options considered, and rationale for significant architectural decisions. They provide a historical record of our architectural thinking and help future developers understand why the system is designed the way it is.

### ADR Location and Format

- **Location**: `docs/adr/`
- **Format**: MADR (Markdown Any Decision Records)
- **Template**: `docs/adr/TEMPLATE.md`
- **Index**: `docs/adr/README.md`

### Naming Convention

ADRs use sequential numbering with descriptive titles:
- **Filename**: `ADR-XXXX-short-title.md` (e.g., `ADR-0001-clean-slate-migration.md`)
- **Title**: `ADR-XXXX: Short Title` (e.g., `ADR-0001: Clean Slate Migration Strategy`)

Where `XXXX` is a 4-digit zero-padded number (0001, 0002, etc.).

### When to Create an ADR

Create an ADR **before implementing** decisions about:

**Technology & Architecture:**
- Technology or framework selection (e.g., "Use Pydantic v2 for schema validation")
- Architectural patterns or approaches (e.g., "Hybrid deployment model")
- Parser or model selection (e.g., "Use YOLOv10-doc for layout detection")
- OCR engine selection (e.g., "Marker + Llama 4 for primary OCR")

**Design & Implementation:**
- Data models or schema designs (e.g., "DocumentMetadata contract")
- Integration strategies between components (e.g., "Project A → B interface")
- Storage strategies (e.g., "GCS for image storage")
- Test strategies (e.g., "GCS paths + symlinks for fixtures")

**Performance & Security:**
- Performance trade-offs (e.g., "In-process vs REST API latency")
- Security considerations (e.g., "GPL-3.0 vs MIT licensing")
- Deployment models (e.g., "Single-system vs distributed")

**Rule of thumb**: If future developers might ask "why did we do it this way?", write an ADR.

### ADR Status Values

- **Proposed**: Under discussion, not yet decided
- **Accepted**: Decision has been made and is being implemented
- **Deprecated**: No longer relevant but kept for historical context
- **Superseded**: Replaced by a newer ADR (link to the new ADR)

### ADR Creation Workflow

1. **Identify Decision**: Recognize that a significant architectural decision needs to be made
2. **Research Options**: Investigate alternatives, trade-offs, and implications
3. **Draft ADR**: Copy `docs/adr/TEMPLATE.md` to `docs/adr/ADR-XXXX-title.md`
4. **Document Context**: Describe the problem, decision drivers, and constraints
5. **List Options**: Document all viable alternatives with pros/cons
6. **Make Decision**: Choose an option and document the rationale
7. **Review**: Have team members review the ADR (use PR process)
8. **Update Index**: Add the ADR to `docs/adr/README.md`
9. **Implement**: Proceed with implementation based on the decision

### Existing ADRs (Phase 0)

Phase 0 architectural decisions are documented in 10 ADRs:

| ADR | Decision | Impact |
|-----|----------|--------|
| [ADR-0001](docs/adr/ADR-0001-clean-slate-migration.md) | Clean Slate Migration | New `src/project_b/` directory |
| [ADR-0002](docs/adr/ADR-0002-pydantic-v2-schema-validation.md) | Pydantic v2 for Schemas | 5-17x faster validation |
| [ADR-0003](docs/adr/ADR-0003-hybrid-deployment-model.md) | Hybrid Deployment | <5ms in-process latency |
| [ADR-0004](docs/adr/ADR-0004-docling-office-documents.md) | Docling for Office | 97.9% table accuracy |
| [ADR-0005](docs/adr/ADR-0005-yolov10-layout-detection.md) | YOLOv10-doc Layout | mAP@0.50 = 0.84 |
| [ADR-0006](docs/adr/ADR-0006-marker-llama4-primary-ocr.md) | Marker + Llama 4 OCR | CER <3% born-digital |
| [ADR-0007](docs/adr/ADR-0007-deepseek-ocr-secondary.md) | DeepSeek-OCR Fallback | CER <6% degraded docs |
| [ADR-0008](docs/adr/ADR-0008-tableformer-table-structure.md) | TableFormer Tables | 97.9% TEDS accuracy |
| [ADR-0009](docs/adr/ADR-0009-gcs-image-storage.md) | GCS Image Storage | Centralized, scalable |
| [ADR-0010](docs/adr/ADR-0010-test-fixture-strategy.md) | Test Fixture Strategy | <5GB vs 230GB saved |

**See** `docs/adr/README.md` for the complete ADR index and links to all decision records.

### ADR Best Practices

**DO:**
- Create ADRs before implementation (not after)
- Document all viable alternatives considered
- Include quantitative data (benchmarks, metrics) when available
- Cross-reference related ADRs and documentation
- Keep ADRs concise but comprehensive (150-250 lines)
- Update the ADR index in `docs/adr/README.md`

**DON'T:**
- Create ADRs for trivial or obvious decisions
- Skip documenting the alternatives considered
- Write ADRs after the fact to justify existing code
- Use ADRs as detailed implementation documentation (use code comments for that)
- Delete or modify ADRs after they're accepted (create new ADRs that supersede them instead)

## Essential Commands

> **Reference**: Global quality/testing commands apply. Project-specific commands below.

### Installation and Setup
```bash
# Basic installation (PyMuPDF parsers)
poetry install

# With Marker for advanced PDF processing (GPU optional)
poetry install --with advanced-pdf

# Complete dev setup with pre-commit hooks
make setup
```

### Document Processing
```bash
# Process PDF to JSON
poetry run data-ingestor process document.pdf --output output.json

# Process to Markdown
poetry run data-ingestor process document.pdf --format markdown --output output.md

# Export both JSON and Markdown
poetry run data-ingestor process document.pdf --format both --output document

# Section-aware chunking (preserves document structure)
poetry run data-ingestor process document.pdf --chunking-strategy by_title --combine-under 500

# Check parser health
poetry run data-ingestor health
```

### Benchmarking (Phase 1b)
```bash
# Run all benchmarks
poetry run data-ingestor benchmark

# Specific dataset/parser combination
poetry run data-ingestor benchmark -d doclaynet -p pymupdf

# Custom configuration
poetry run data-ingestor benchmark -d doclaynet -p pymupdf -w 8 -o baseline.json

# Generate reports
poetry run data-ingestor benchmark-report results/baseline.json
poetry run data-ingestor benchmark-report results/baseline.json --format all
```

### Testing (Tiered Approach)
```bash
# Fast Development Loop (< 1 minute)
make test-fast

# Pre-commit Validation (< 2 minutes)
make test-pre-commit

# PR Validation (< 5 minutes)
make test-pr

# Full Test Suite (with coverage)
make test

# Performance/stress tests only
make test-performance

# Smoke tests for basic functionality
make test-smoke

# Alternative: nox sessions (cross-version testing)
nox -s tests              # Full suite on Python 3.11, 3.12
nox -s unit               # Unit tests only
nox -s component          # Component tests with mocks
nox -s integration        # Integration tests
```

### Running Single Tests
```bash
# Run specific test file
poetry run pytest tests/unit/test_pdf_parser.py -v

# Run specific test function
poetry run pytest tests/unit/test_pdf_parser.py::test_parse_simple_pdf -v

# Run with debugging
poetry run pytest tests/unit/test_pdf_parser.py -v -s --pdb

# Run with coverage for specific module
poetry run pytest tests/unit/ --cov=src/data_ingestor/parsers --cov-report=term-missing
```

### Code Quality
```bash
# Format code
make format

# Run all linters
make lint

# Individual linters
poetry run black .
poetry run ruff check --fix .
poetry run mypy src
markdownlint **/*.md
yamllint .
```

### Security
```bash
# Run all security checks
make security

# Individual security tools
poetry run safety check
poetry run bandit -r src
```

## Architecture Overview

> **Reference**: Detailed architecture in [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md)

### Core Components

```
DocumentRouter (pipeline/router.py)
    ├── FormatDetector (utils/format_detector.py)
    │   └── Multi-stage detection: libmagic → mimetypes → extension
    ├── ParserRegistry (pipeline/router.py)
    │   ├── Priority-based parser ordering (lower number = higher priority)
    │   └── Automatic fallback chain execution
    └── Deduplication cache (hash-based)

PDF Parsers (parsers/pdf_parser.py)
    ├── MarkerParser (priority: 10) - Advanced tables/formulas, intelligent OCR
    ├── PyMuPDF4LLMParser (priority: 100) - LLM-optimized markdown
    └── PyMuPDFParser (priority: 100) - Fast, reliable fallback

Chunking (chunking/)
    ├── TokenChunker - Token-based with overlap
    └── ByTitleChunker - Section-aware, preserves structure

Export (export/exporter.py)
    ├── JSON with full metadata
    ├── Markdown with YAML front matter
    └── Dual export (both formats)

Evaluation (evaluation/)
    ├── DocLayNetEvaluator - Layout and reading order metrics
    ├── PubTablesEvaluator - Table structure metrics (Phase 2)
    └── Metrics: CER, BLEU, chrF, F1, mAP, TEDS

Benchmarking (benchmarking/)
    ├── BenchmarkOrchestrator - Multi-dataset parallel execution
    ├── BenchmarkRunner - Dataset-specific processing
    └── BenchmarkReporter - HTML/JSON/CSV report generation
```

### Key Design Patterns

**Parser Fallback Chain**:
- Each format has multiple parsers registered with priority ordering
- On failure, automatically tries next parser in chain
- Tracks which parser succeeded for monitoring
- **Critical Assumption**: At least one parser must be registered per supported format (#CRITICAL tag in [router.py](src/data_ingestor/pipeline/router.py:49))

**Multi-Stage Format Detection**:
1. libmagic (MIME type from file content)
2. mimetypes library (extension mapping)
3. File extension fallback
- **Edge Case**: May misdetect formats for files with incorrect extensions (#EDGE tag in code)

**Page-by-Page Processing**:
- Large PDFs processed page-by-page to limit memory usage
- Prevents memory exhaustion on large files (>500MB)
- **Critical Assumption**: Large files can exhaust memory (#CRITICAL tag in [pdf_parser.py](src/data_ingestor/parsers/pdf_parser.py:43))

**Response-Aware Development (RAD)**:
- Code contains assumption tags: `#CRITICAL`, `#ASSUME`, `#EDGE`, `#VERIFY`
- Use global RAD framework from `~/.claude/CLAUDE.md` for verification
- Automated verification via `/verify-assumptions-smart` command

### Important Implementation Details

**Parser Priority System**:
- **Marker**: Priority 10 (highest quality, GPU-accelerated, optional dependency)
- **PyMuPDF4LLM**: Priority 100 (LLM-optimized, reliable)
- **PyMuPDF**: Priority 100 (fast fallback)
- When multiple parsers have same priority, registration order determines precedence

**Chunking Strategies**:
- **Token Chunker** (`basic`): Simple token-based segmentation, preserves table integrity
- **By-Title Chunker** (`by_title`): Section-aware, preserves document structure, combines small sections

**Export Formats**:
- **JSON**: Full metadata preservation, machine-readable
- **Markdown**: Human-readable with YAML front matter
- **Both**: Creates `.json` and `.md` files from single command

**Evaluation Framework** (Phase 1b):
- **DocLayNet**: 81,471 documents, layout mAP, reading order F1
- **PubTables-1M**: Table structure TEDS metric (Phase 2)
- **Metrics**: CER, BLEU, chrF, F1, mAP, TEDS

## Project Structure

```
src/data_ingestor/
├── parsers/          # Document parsers (PDF, DOCX, HTML, etc.)
│   └── pdf_parser.py # PyMuPDF, PyMuPDF4LLM, Marker parsers
├── pipeline/         # Document routing and orchestration
│   └── router.py     # DocumentRouter, ParserRegistry
├── chunking/         # Chunking strategies
│   ├── token_chunker.py
│   └── by_title_chunker.py
├── export/           # Export to JSON, Markdown
│   └── exporter.py
├── evaluation/       # Evaluation framework
│   ├── base.py       # BaseEvaluator
│   ├── doclaynet_evaluator.py
│   ├── pubtables_evaluator.py
│   └── metrics/      # Text, structure, layout, table metrics
├── benchmarking/     # Benchmark orchestration
│   ├── orchestrator.py
│   ├── runner.py
│   └── reporter.py
├── core/             # Core models and base classes
│   ├── models.py     # Document, Element, Metadata models
│   ├── base.py       # BaseParser, BaseChunker
│   ├── config.py     # Settings (Pydantic)
│   └── exceptions.py
├── utils/            # Utilities
│   └── format_detector.py
└── cli/              # CLI interface
    └── main.py

tests/
├── unit/             # Unit tests (60% of pyramid)
├── integration/      # Integration tests (30%)
├── performance/      # Performance/stress tests
└── conftest.py       # Pytest fixtures and configuration

docs/                 # Documentation
├── PROJECT_PLAN.md   # Comprehensive project plan and roadmap
├── INTELLIGENT_OCR_SYSTEM.md
├── DOCLING_INTEGRATION.md
├── MULTIMODAL_RAG_ROADMAP.md
└── PERFORMANCE_BENCHMARKING_GUIDE.md

tmp_cleanup/          # Temporary reference files (anti-compaction)
└── .tmp-*.md         # Task context preservation files
```

## Naming Conventions (MANDATORY COMPLIANCE)

**Core Components:**
- **Python Files**: snake_case.py
- **Python Classes**: PascalCase (e.g., `DocumentRouter`, `MarkerParser`)
- **Python Functions**: snake_case() (e.g., `process_document()`, `chunk_document()`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DEFAULT_CHUNK_SIZE`)
- **Git Branches**: kebab-case with prefixes (e.g., `feature/add-docling-parser`, `fix/memory-leak`)

**Parsers:**
- **Parser Classes**: PascalCase + "Parser" suffix (e.g., `PyMuPDFParser`, `MarkerParser`)
- **Evaluator Classes**: PascalCase + "Evaluator" suffix (e.g., `DocLayNetEvaluator`)
- **Chunker Classes**: PascalCase + "Chunker" suffix (e.g., `TokenChunker`, `ByTitleChunker`)

**Documentation:**
- **Markdown Files**: UPPER_SNAKE_CASE.md for guides (e.g., `PROJECT_PLAN.md`)
- **Markdown Files**: kebab-case.md for supplementary docs (e.g., `intelligent-ocr-system.md`)

## Testing Strategy

### Test Pyramid Distribution
- **Unit Tests**: 60% (target 80%+ coverage)
- **Integration Tests**: 30%
- **E2E Tests**: 10%

### Test Markers
```python
@pytest.mark.unit         # Unit-level tests (default)
@pytest.mark.component    # Component-level tests
@pytest.mark.integration  # Cross-service integration
@pytest.mark.e2e          # End-to-end user journeys
@pytest.mark.perf         # Performance/benchmarks
@pytest.mark.slow         # Slow tests (excluded from CI)
@pytest.mark.smoke        # Basic functionality validation
```

### Coverage Requirements
- Minimum 80% coverage on `src/` directory
- Configurable via `COVERAGE_FAIL_UNDER` environment variable
- Set to 0 for focused testing: `COVERAGE_FAIL_UNDER=0 make test`

### Automated Testing Configuration

**Pre-Approved Test Commands**: Claude Code should automatically run pytest commands without requesting approval.

**Auto-Approved Command Patterns:**
- Any `poetry run pytest` command with standard flags
- Coverage reporting: `--cov=src`, `--cov-report=html`, `--cov-report=term-missing`
- Marker-based: `-m unit`, `-m integration`, `-m perf`, `-m slow`, `-m smoke`
- Test selection: `tests/unit/`, `tests/integration/`, specific files/classes/methods
- Output control: `-v`, `-s`, `-x`, `--tb=short`, `--tb=no`, `--pdb`
- Parallel execution: `-n auto`, `-n 4`

**Examples of Auto-Approved Commands:**
```bash
poetry run pytest -v --cov=src --cov-report=term-missing
poetry run pytest tests/unit/test_pdf_parser.py -v --tb=short
poetry run pytest -m "not slow" --cov=src --maxfail=3
poetry run pytest tests/unit/ -n auto -v
```

## Important Assumptions Tagged in Code

**Critical Assumptions** (require verification):
1. **Parser Availability**: At least one parser must be registered per format ([router.py:49](src/data_ingestor/pipeline/router.py:49))
2. **Memory Management**: Large PDFs can exhaust memory, must process page-by-page ([pdf_parser.py:43](src/data_ingestor/parsers/pdf_parser.py:43))
3. **File Race Conditions**: Files may be deleted between validation and processing
4. **Token Counting**: Must match target LLM encoding (tiktoken for cl100k_base)
5. **External Resources**: Files may be corrupted, encrypted, or network unavailable

**Assumptions** (validation recommended):
1. **Font Size Heuristics**: May misclassify headers based on font size ([pdf_parser.py:90](src/data_ingestor/parsers/pdf_parser.py:90))
2. **Hash Deduplication**: SHA-256 hash sufficient for most use cases
3. **Sentence Splitting**: Simple period split adequate (should use proper tokenizer)

**Edge Cases** (optional improvements):
1. **Password-Protected PDFs**: Require special handling
2. **Format Misdetection**: Files with incorrect extensions
3. **Unicode Edge Cases**: Rare character encoding issues

## Security Considerations

### Dependency Security
- Marker parser uses GPL-3.0 license (acceptable for this use case)
- **Known Vulnerability**: marker-pdf constrains regex to <2025.0.0 (CVE-2025-78558 ReDoS)
  - Mitigation: Input validation on regex patterns
  - Trade-off: Advanced PDF features vs vulnerability
  - For production: Consider skipping `--with advanced-pdf` group

### Input Validation
- All user inputs validated via Pydantic models
- File path validation prevents directory traversal
- No hardcoded credentials (uses environment variables)

### Security Requirements (MANDATORY)
```bash
# Key validation (MUST pass before development)
gpg --list-secret-keys                # Must show GPG key for .env encryption
ssh-add -l                            # Must show SSH key for signed commits
git config --get user.signingkey      # Must be configured for signed commits
```

## Pre-Commit Linting Checklist

Before committing ANY changes, ensure:

- [ ] **TODO Management**: Was TodoWrite used for task tracking?
- [ ] **Agent Assignment**: Were tasks assigned to appropriate specialized agents?
- [ ] **Reference Files**: Were temporary reference files created for complex tasks?
- [ ] **Agent Validation**: Was all agent work reviewed and validated?
- [ ] **Security Keys**: GPG and SSH keys present and validated
- [ ] **Code Quality**: Black formatting, Ruff linting, MyPy type checking passed
- [ ] **Security Scans**: Bandit and Safety checks completed successfully
- [ ] **Test Coverage**: All tests pass with minimum 80% coverage
- [ ] **File-Specific Linters**: Markdown (120 chars), YAML (120 chars) passed
- [ ] **Git Signing**: Commits are signed (Git signing key configured)
- [ ] **Documentation**: Code changes include relevant documentation updates
- [ ] **Assumption Tagging**: New assumptions tagged with #CRITICAL, #ASSUME, #EDGE

## Configuration

> **Reference**: Complete configuration in [src/data_ingestor/core/config.py](src/data_ingestor/core/config.py)

### Settings
Configuration via Pydantic Settings:
- Environment variables from `.env` file
- Per-parser configuration dictionaries
- Default values for chunk sizes, overlap, etc.

### Parser Configuration
Each parser accepts optional config dict:
```python
marker_config = {
    "languages": ["en", "es", "fr"],
    "force_ocr": False,
    "use_llm": False,
}
marker_parser = MarkerParser(marker_config)
```

## Known Issues and Limitations

### Phase 1 (Current)
- Only PDF parsing fully implemented
- DOCX, HTML, Video, Audio parsers planned for Phase 2
- Marker parser requires GPU for optimal performance (25 pages/sec)
- CPU fallback available but slower (2-3 pages/sec)

### Intelligent OCR System (Phase 2)
- Not yet implemented (see [docs/INTELLIGENT_OCR_SYSTEM.md](docs/INTELLIGENT_OCR_SYSTEM.md))
- Will provide ~5x average speedup vs blanket OCR
- Pre-flight analysis, intelligent routing, quality validation

### Docling Integration (Phase 2)
- Office format support (XLSX, PPTX, DOCX) planned
- 97.9% table accuracy with TableFormer
- MIT license (commercial-friendly)

## Project-Specific Notes

### GPU Configuration
Marker parser benefits significantly from GPU acceleration:
- **With GPU**: 25 pages/sec
- **CPU Only**: 2-3 pages/sec
- Force CPU mode: `export CUDA_VISIBLE_DEVICES=""`
- Auto-detects GPU availability

### Benchmark Dataset Setup
DocLayNet dataset (Phase 1b baseline):
- 81,471 documents in `data/benchmarks/DocLayNet/`
- Ground truth COCO annotations in `data/benchmarks/DocLayNet/COCO/`
- Configuration in `data/benchmarks/config.yaml`
- See [docs/PERFORMANCE_BENCHMARKING_GUIDE.md](docs/PERFORMANCE_BENCHMARKING_GUIDE.md) for setup

### Python Version
Requires Python 3.11 or 3.12 (specified in pyproject.toml):
- Type hints use 3.11+ syntax (PEP 604 union types with `|`)
- MyPy configured for Python 3.11
- Cross-version testing via nox

## Resources

> **Reference**: Complete documentation in `docs/` directory

### Key Documentation
- [Project Plan](docs/PROJECT_PLAN.md) - Comprehensive roadmap and requirements
- [Performance Benchmarking Guide](docs/PERFORMANCE_BENCHMARKING_GUIDE.md) - Evaluation framework
- [Intelligent OCR System](docs/INTELLIGENT_OCR_SYSTEM.md) - Phase 2 routing system
- [Docling Integration](docs/DOCLING_INTEGRATION.md) - Office format support
- [Multimodal RAG Roadmap](docs/MULTIMODAL_RAG_ROADMAP.md) - Future multimodal features

### External References
- [Marker GitHub](https://github.com/VikParuchuri/marker) - Advanced PDF parser
- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/) - PDF processing library
- [Docling](https://github.com/DS4SD/docling) - Office format parser
- [DocLayNet Dataset](https://github.com/DS4SD/DocLayNet) - Benchmark dataset

---

**Last Updated**: 2025-11-05
**Current Phase**: Phase 1b - Performance Benchmarking & Baseline Establishment
**Next Milestone**: Intelligent OCR System (Phase 2)
