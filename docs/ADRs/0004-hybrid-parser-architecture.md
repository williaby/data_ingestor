# ADR-004: Hybrid PDF Parser Architecture

**Status**: ✅ **Accepted**
**Date**: 2025-11-17
**Deciders**: Byron Williams
**Tags**: architecture, parsers, pdf, document-processing

## Context

Document processing for RAG applications requires extracting structured content from diverse PDF formats:

### Requirements

1. **Accuracy**: Preserve tables, formulas, complex layouts
2. **Performance**: Process large documents efficiently (<10s for typical PDFs)
3. **Flexibility**: Handle scanned PDFs, born-digital PDFs, complex layouts
4. **Licensing**: Balance GPL constraints with feature requirements
5. **Reliability**: Automatic fallback when primary parser fails

### Parser Options Evaluated

1. **PyMuPDF**
   - License: AGPL-3.0 / Commercial
   - Speed: Very fast (~100 pages/sec)
   - Accuracy: Good for simple layouts, struggles with complex tables
   - Tables: Basic detection, limited structure

2. **Marker**
   - License: GPL-3.0
   - Speed: Moderate (~25 pages/sec with GPU, ~2-3 pages/sec CPU)
   - Accuracy: Excellent for tables, formulas, complex layouts
   - Tables: Advanced detection with TableFormer
   - OCR: Intelligent routing (only when needed)

3. **PyMuPDF4LLM**
   - License: AGPL-3.0 / Commercial
   - Speed: Fast (~50 pages/sec)
   - Accuracy: Optimized for LLM consumption
   - Output: Clean markdown format

4. **Docling** (Phase 2)
   - License: MIT
   - Speed: Moderate
   - Accuracy: 97.9% table accuracy
   - Formats: DOCX, XLSX, PPTX support

## Decision

**Implement a hybrid parser architecture with priority-based automatic fallback.**

### Architecture

```python
ParserRegistry:
  - MarkerParser (priority: 10)      # Highest quality, optional
  - PyMuPDF4LLMParser (priority: 100) # LLM-optimized, reliable
  - PyMuPDFParser (priority: 100)     # Fast fallback

DocumentRouter:
  - Detect format (libmagic → mimetypes → extension)
  - Select parsers by priority (lowest number = highest priority)
  - Execute parser chain with automatic fallback
  - Cache results to avoid reprocessing
```

### Parser Selection Logic

1. **Primary**: Marker (if installed, GPU optional)
   - Use for: Complex tables, formulas, scanned PDFs
   - Fallback: On failure or if not installed

2. **Secondary**: PyMuPDF4LLM
   - Use for: LLM-optimized markdown output
   - Fallback: On failure

3. **Tertiary**: PyMuPDF
   - Use for: Fast processing, simple layouts
   - Fallback: Final safety net

### Installation Tiers

```bash
# Tier 1: Basic (PyMuPDF only)
poetry install

# Tier 2: Advanced (includes Marker)
poetry install --with advanced-pdf

# Tier 3: Complete (includes Docling - Phase 2)
poetry install --with advanced-pdf --with office-formats
```

## Consequences

### Positive

1. **Flexibility**: Multiple parsers for different document types
2. **Reliability**: Automatic fallback prevents parsing failures
3. **Performance**: Fast parsers for simple cases, slow parsers only when needed
4. **Quality**: Best-in-class table extraction when Marker is available
5. **Licensing**: GPL-3.0 is optional (Marker), core functionality remains permissive

### Negative

1. **Complexity**: Multiple parsers increase maintenance burden
2. **Dependencies**: Optional dependencies complicate installation
3. **Licensing**: GPL-3.0 may limit commercial use (if Marker is installed)
4. **Configuration**: Users must choose installation tier
5. **Testing**: Need to test all parser combinations

### Trade-offs

**GPL-3.0 Acceptance Rationale**:
- Document processing use case (not library embedding)
- Optional dependency (users can skip Marker)
- Superior quality justifies license constraint
- Known vulnerability in marker-pdf (CVE-2025-78558 ReDoS) - mitigated by input validation

**Performance vs Quality**:
- Simple PDFs: PyMuPDF (~100x faster than Marker)
- Complex PDFs: Marker (5-10x better table accuracy)
- Automatic routing balances both

## Implementation Details

### Parser Priority System

```python
class ParserRegistry:
    def register(self, format: str, parser: BaseParser, priority: int):
        """Lower priority number = higher precedence."""
        parsers = self._parsers.get(format, [])
        parsers.append((priority, parser))
        parsers.sort(key=lambda x: x[0])  # Sort by priority
        self._parsers[format] = parsers
```

### Fallback Chain

```python
for priority, parser in parsers:
    try:
        result = parser.parse(file_path)
        logger.info(f"Successfully parsed with {parser.__class__.__name__}")
        return result
    except Exception as e:
        logger.warning(f"{parser.__class__.__name__} failed, trying next...")
        continue

raise ParsingError("All parsers failed")
```

## Related Decisions

- ADR-007: Intelligent OCR System (Phase 2)
- ADR-008: Docling Integration (Phase 2)

## References

- [Marker GitHub](https://github.com/VikParuchuri/marker)
- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)
- [GPL-3.0 License](https://www.gnu.org/licenses/gpl-3.0.en.html)
- [DocLayNet Benchmark](https://github.com/DS4SD/DocLayNet)
