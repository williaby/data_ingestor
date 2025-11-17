---
name: Parser Issue
about: Report parsing errors or quality issues with specific document types
title: '[PARSER] '
labels: parser, quality
assignees: ''
---

## Parser Information

- **Parser**: (PyMuPDF, Marker, Docling, PyMuPDF4LLM, etc.)
- **Parser version**:
- **Configuration**: (any custom config used)

## Document Information

- **File type**: (PDF, DOCX, HTML, etc.)
- **File size**:
- **Number of pages**: (if applicable)
- **Document features**:
  - [ ] Tables
  - [ ] Images
  - [ ] Formulas/equations
  - [ ] Multiple columns
  - [ ] Scanned/OCR content
  - [ ] Complex layouts
  - [ ] Non-English text
  - [ ] Special characters

## Issue Description

Describe what's wrong with the parsing output:

### Expected Output

What should the parser extract or how should it structure the content?

### Actual Output

What did the parser actually produce?

```
Paste relevant parsing output here
```

## Quality Metrics (if applicable)

- **Text accuracy**: (estimated %)
- **Table detection**: (tables found vs. expected)
- **Layout preservation**: (good/fair/poor)
- **Processing time**:

## Sample Document

Can you provide a sample document that reproduces this issue?

- [ ] Yes, attached
- [ ] Yes, but contains sensitive data (can provide redacted version)
- [ ] No, proprietary/confidential

## Workarounds Tried

What have you tried to work around this issue?

- [ ] Different parser
- [ ] Custom configuration
- [ ] Pre-processing
- [ ] Post-processing

## Additional Context

Add any other context, screenshots, or examples:
- Comparison with other parsers
- Related issues
- Expected use case impact
