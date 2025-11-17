# ADR-0001: Clean Slate Migration Strategy

**Status**: Accepted
**Date**: 2025-11-17
**Deciders**: Claude Code, Project Lead
**Technical Story**: Sprint 0.1.2 - Migration Strategy Decision (Q6, Q9 Resolution)

## Context and Problem Statement

The legacy `data_ingestor` implementation (v1.0) was designed as a monolithic document parsing and chunking pipeline. However, the new 4-project RAG pipeline architecture requires fundamentally different responsibilities for Project B (Layout, OCR & Structural Extraction Engine). How should we approach the migration from the legacy codebase to the new Project B implementation while preserving institutional knowledge and enabling potential rollback?

The legacy system focused on end-to-end document processing (parsing → chunking → export), while Project B must focus exclusively on layout detection, reading order prediction, OCR orchestration, and structure assembly. This represents a significant architectural divergence that impacts code organization, data models, and technology stack.

## Decision Drivers

* **Architectural Changes**: Project B has fundamentally different responsibilities (layout/OCR) vs. legacy (parsing/chunking/export)
* **Schema Changes**: New Pydantic v2 schemas (DocumentMetadata input, OCRDocument output) replace Unstructured.io-based models
* **Technology Stack**: New core technologies (YOLOv10-doc, Marker+Llama4, Docling, TableFormer) require different integration patterns
* **Clean Boundaries**: Separation of concerns across 4 projects (A→B→C→D) requires clear interfaces and contracts
* **Code Reusability**: ~30-40% of legacy code (evaluation, benchmarking, utils) should be preserved with refactoring
* **Knowledge Preservation**: Need to maintain access to legacy implementation for reference and learning
* **Rollback Capability**: Must enable rollback if critical issues arise during migration
* **Development Velocity**: Need to move quickly without being constrained by legacy architecture

## Considered Options

* **Option 1: Clean Slate Migration** - Create new `src/project_b/` directory, preserve legacy via git tag + reference branch
* **Option 2: Incremental Refactoring** - Gradually refactor existing codebase in-place, maintaining backward compatibility
* **Option 3: Gradual Migration** - Maintain parallel implementations, gradually deprecate legacy components
* **Option 4: Fork and Diverge** - Create separate repository, sever connection to legacy codebase

## Decision Outcome

**Chosen option**: "Option 1: Clean Slate Migration", because it provides the cleanest separation between legacy and new architectures while preserving the ability to reference legacy code and rollback if needed.

### Implementation Details

1. **Legacy Preservation**:
   - Git tag: `v1.0-legacy` at commit `b4fba4a` (Phase 1C completion)
   - Reference branch: `legacy/data-ingestor-v1` (permanent, never merged)

2. **New Implementation**:
   - Location: `src/project_b/` (completely separate from `src/data_ingestor/`)
   - Structure: 7 core modules (layout, reading_order, ocr, structure, specialized, schemas, pipeline)

3. **Code Reuse Strategy**:
   - Keep with refactoring: ~30-40% (evaluation framework, benchmarking infrastructure, core utilities)
   - Discard: ~60-70% (parsers, chunking, export, quality inspection, legacy CLI)
   - New code: ~4,700-6,800 LOC

### Positive Consequences

* **Clean Architecture**: No legacy constraints on new design decisions
* **Clear Separation**: Distinct responsibilities between Projects A, B, C, D enforced at directory level
* **Faster Development**: No need to maintain backward compatibility during active development
* **Knowledge Preservation**: Legacy code remains accessible via git tag and reference branch
* **Rollback Capability**: Can return to `v1.0-legacy` if critical issues arise
* **Fresh Dependencies**: Can adopt new dependency versions (Pydantic v2, ultralytics) without migration concerns
* **Simplified Testing**: New test suite focused on layout/OCR without legacy test baggage

### Negative Consequences

* **Temporary Code Duplication**: Some utilities will exist in both `src/data_ingestor/` and `src/project_b/` during transition
* **Learning Curve**: Developers must understand both legacy (for reference) and new (for development) codebases
* **Migration Effort**: ~4,700-6,800 LOC of new code required vs. incremental refactoring approach
* **Evaluation Framework Migration**: DocLayNet and PubTables evaluators must be adapted to new schemas
* **Documentation Burden**: Must document both migration strategy and new architecture comprehensively

## Pros and Cons of the Options

### Option 1: Clean Slate Migration

**Pros:**
* Good, because it provides complete architectural freedom for Project B design
* Good, because legacy code remains intact and accessible for reference
* Good, because rollback is simple and reliable (git checkout v1.0-legacy)
* Good, because it enforces clean separation of concerns across 4-project pipeline
* Good, because new team members have clear starting point without legacy confusion
* Good, because testing infrastructure can be designed from scratch for layout/OCR focus

**Cons:**
* Bad, because it requires ~4,700-6,800 LOC of new code vs. gradual refactoring
* Bad, because evaluation framework migration requires schema adaptation effort
* Bad, because temporary code duplication increases maintenance burden during transition
* Bad, because institutional knowledge embedded in legacy code structure may be lost

### Option 2: Incremental Refactoring

**Pros:**
* Good, because it minimizes code rewriting (gradual evolution vs. revolution)
* Good, because backward compatibility can be maintained during transition
* Good, because existing tests continue to pass during refactoring process
* Good, because institutional knowledge embedded in code structure is preserved

**Cons:**
* Bad, because legacy architecture constraints slow down new feature development
* Bad, because maintaining backward compatibility increases complexity significantly
* Bad, because schema changes (Unstructured.io → Pydantic v2) create breaking changes anyway
* Bad, because parser-focused code (60-70%) must be discarded regardless of approach
* Bad, because mixing legacy and new patterns creates confusion and technical debt

### Option 3: Gradual Migration

**Pros:**
* Good, because it allows A/B testing between legacy and new implementations
* Good, because production systems can continue using legacy during migration
* Good, because rollback is easy (just keep using legacy implementation)
* Good, because parallel implementation validates new design against legacy behavior

**Cons:**
* Bad, because maintaining two implementations doubles maintenance burden
* Bad, because it increases codebase complexity with parallel paths
* Bad, because deprecation timeline creates uncertainty for downstream consumers
* Bad, because infrastructure must support both implementations (testing, deployment, monitoring)
* Bad, because schema incompatibility (Unstructured.io vs. Pydantic v2) makes true parallelism difficult

### Option 4: Fork and Diverge

**Pros:**
* Good, because it provides complete separation with no cross-contamination
* Good, because repository size and git history remain small and focused
* Good, because dependency conflicts are eliminated entirely

**Cons:**
* Bad, because it severs connection to legacy code (harder to reference)
* Bad, because rollback requires switching repositories (more complex)
* Bad, because shared utilities (logging, config) must be duplicated or extracted to library
* Bad, because git blame and history context is lost for migrated code
* Bad, because it complicates monorepo strategy if 4 projects share infrastructure

## Links

* [Related to] [ADR-0002: Pydantic v2 for Schema Validation](ADR-0002-pydantic-v2-schema-validation.md) - Schema changes motivate clean slate
* [Related to] [ADR-0003: Hybrid Deployment Model](ADR-0003-hybrid-deployment-model.md) - Deployment strategy differs from legacy
* [References] [docs/MIGRATION.md](../MIGRATION.md) - Detailed migration guide and timeline
* [References] [docs/PROJECT_PLAN.md](../PROJECT_PLAN.md) - 18-week implementation plan for Project B
* [References] Legacy code: `git checkout v1.0-legacy` or `git checkout legacy/data-ingestor-v1`

---

## Notes

**Legacy Code Statistics (v1.0-legacy)**:
- Total LOC: ~8,000 lines (src/data_ingestor/)
- Keep with refactoring: ~2,400-3,200 LOC (evaluation, benchmarking, utils)
- Discard: ~4,800-5,600 LOC (parsers, chunking, export, quality)

**Project B Statistics (Target)**:
- New LOC: ~4,700-6,800 LOC (layout, reading_order, ocr, structure, specialized)
- Migrated LOC: ~2,400-3,200 LOC (evaluation, benchmarking, utils - refactored)
- Total LOC: ~7,100-10,000 LOC

**Migration Timeline**:
- Phase 0: Foundation & Planning (Weeks 1-2) - Tag legacy, set up new structure
- Phase 1-7: Implementation (Weeks 3-16) - Build Project B incrementally
- Phase 8: Documentation & Handoff (Weeks 17-18) - Migration complete

**Rollback Tested**: Confirmed `git checkout v1.0-legacy` restores fully functional legacy implementation with Phase 1C benchmarking baseline.
