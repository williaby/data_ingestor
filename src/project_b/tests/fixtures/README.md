# Test Fixtures and Data Strategy

## Overview

This directory contains test fixtures for Project B unit, integration, and component tests.

## Dataset Storage Strategy

**IMPORTANT**: All testing, training, and benchmark datasets are stored in:
1. **GCS (Google Cloud Storage)**: Production datasets with corrected images from Project A
2. **Image Generator Project**: Reference datasets and training data

### Guidelines

**DO NOT duplicate dataset storage. Instead:**

1. **For Real Datasets**: Use GCS paths in test fixtures
   - Example: `gs://test-bucket/corrected/sample_page_001.png`
   - Tests requiring real data should use GCS client (mocked in unit tests)

2. **For Local Development**: Create symlinks to image generator project datasets
   ```bash
   # Example (when image generator project exists):
   ln -s /path/to/image_generator/datasets ./fixtures/datasets
   ```

3. **For Unit Tests**: Create minimal synthetic fixtures only
   - Small 1x1 pixel PNG images for testing image loading
   - Mock DocumentMetadata JSON with minimal required fields
   - Focus on testing logic, not real data processing

## Fixture Types

### Minimal Synthetic Fixtures (Unit Tests)
- `mock_document_metadata.json` - Minimal valid DocumentMetadata
- `mock_1x1_image.png` - 1x1 transparent PNG for image loading tests
- `mock_layout_blocks.json` - Sample layout detection output
- `mock_ocr_result.json` - Sample OCR engine output

### Real Dataset Access (Integration/E2E Tests)
- Use GCS paths from DocumentMetadata
- Use google-cloud-storage client to fetch images
- Mock GCS client in component tests, use real client in integration tests

## Test Data Hierarchy

```
tests/fixtures/
├── README.md (this file)
├── mock_documents/          # Minimal synthetic JSON fixtures
├── mock_images/             # Minimal synthetic images (1x1 PNG)
├── mock_layout/             # Sample layout detection outputs
├── mock_ocr/                # Sample OCR engine outputs
└── datasets/                # SYMLINK to image generator project (when available)
```

## Adding New Fixtures

When adding new test fixtures:

1. **Unit tests**: Create minimal synthetic data in `mock_*` directories
2. **Integration tests**: Reference GCS paths or symlinked datasets
3. **E2E tests**: Use real GCS datasets with proper authentication

## GCS Authentication (Integration/E2E Tests)

Tests requiring real GCS access need:
- `GOOGLE_APPLICATION_CREDENTIALS` environment variable
- Service account with read access to test buckets
- Mock GCS client for component tests (see `conftest.py`)

---

**Last Updated**: 2025-11-17
**Related Sprints**: Sprint 0.3.1, 0.3.2, 0.3.3
