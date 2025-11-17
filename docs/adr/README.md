# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) for Project B (Layout, OCR & Structural Extraction Engine).

## What are ADRs?

Architecture Decision Records document significant architectural decisions made during the project. Each ADR describes:
- The context and problem we faced
- The options we considered
- The decision we made and why
- The consequences (both positive and negative) of that decision

ADRs provide a historical record of our architectural thinking and help future developers understand why the system is designed the way it is.

## ADR Format

We use the **MADR (Markdown Any Decision Records)** format. See [TEMPLATE.md](TEMPLATE.md) for the ADR template.

## Naming Convention

ADRs are numbered sequentially with the format:
- **Filename**: `ADR-XXXX-short-title.md` (e.g., `ADR-0001-clean-slate-migration.md`)
- **Title**: `ADR-XXXX: Short Title` (e.g., `ADR-0001: Clean Slate Migration Strategy`)

Where `XXXX` is a 4-digit zero-padded number (0001, 0002, etc.).

## Status Values

ADRs can have the following status values:
- **Proposed**: Under discussion, not yet decided
- **Accepted**: Decision has been made and is being implemented
- **Deprecated**: No longer relevant but kept for historical context
- **Superseded**: Replaced by a newer ADR (link to the new ADR should be provided)

## When to Create an ADR

Create an ADR when making decisions about:
- Technology or framework selection
- Architectural patterns or approaches
- Integration strategies between components
- Data models or schema designs
- Deployment models
- Security or performance trade-offs
- Major refactoring or migration strategies

**Rule of thumb**: If future developers might ask "why did we do it this way?", write an ADR.

## ADR Index

### Phase 0: Foundation & Planning

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-0001](ADR-0001-clean-slate-migration.md) | Clean Slate Migration Strategy | Accepted | 2025-11-17 |
| [ADR-0002](ADR-0002-pydantic-v2-schema-validation.md) | Pydantic v2 for Schema Validation | Accepted | 2025-11-17 |
| [ADR-0003](ADR-0003-hybrid-deployment-model.md) | Hybrid Deployment Model | Accepted | 2025-11-17 |
| [ADR-0004](ADR-0004-docling-office-documents.md) | Docling for Office Documents | Accepted | 2025-11-17 |
| [ADR-0005](ADR-0005-yolov10-layout-detection.md) | YOLOv10-doc for Layout Detection | Accepted | 2025-11-17 |
| [ADR-0006](ADR-0006-marker-llama4-primary-ocr.md) | Marker + Llama 4 for Primary OCR | Accepted | 2025-11-17 |
| [ADR-0007](ADR-0007-deepseek-ocr-secondary.md) | DeepSeek-OCR via Modal for Secondary OCR | Accepted | 2025-11-17 |
| [ADR-0008](ADR-0008-tableformer-table-structure.md) | TableFormer for Table Structure | Accepted | 2025-11-17 |
| [ADR-0009](ADR-0009-gcs-image-storage.md) | GCS for Image Storage | Accepted | 2025-11-17 |
| [ADR-0010](ADR-0010-test-fixture-strategy.md) | Test Fixture Strategy (GCS/Symlinks) | Accepted | 2025-11-17 |

### Future Phases

ADRs for future phases (Phase 1, 2, 3, 4) will be added as architectural decisions are made during implementation.

## References

- **MADR**: https://adr.github.io/madr/
- **ADR Best Practices**: https://github.com/joelparkerhenderson/architecture-decision-record
- **Project B Documentation**: [../PROJECT_PLAN.md](../PROJECT_PLAN.md)

---

**Last Updated**: 2025-11-17
**Total ADRs**: 10 (Phase 0)
