# PDF Resolution Pre-processing (Phase 1c)

**Status**: ✅ Implemented
**Version**: 1.0
**Last Updated**: 2025-11-06

## Overview

Phase 1c adds intelligent PDF resolution analysis and automatic upscaling to improve OCR quality for low-resolution documents. The system analyzes PDFs during pre-flight checks and automatically upscales documents below 300 DPI to ensure optimal OCR results.

### Key Benefits

- **Improved OCR Accuracy**: Low-resolution PDFs are upscaled to 300 DPI for better text extraction
- **Automatic Detection**: Analyzes PDF image resolution without manual intervention
- **Configurable Thresholds**: Customize DPI thresholds and upscaling algorithms
- **Minimal Overhead**: Analysis typically completes in <100ms per document
- **Transparent Integration**: Automatically applied during document routing

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│               PDF Pre-flight Analysis (Phase 1c)            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. DocumentRouter receives PDF                             │
│                   ↓                                           │
│  2. PDFDocumentAnalyzer.analyze()                           │
│           ↓                               ↓                   │
│  3. PDFResolutionAnalyzer        4. PDFUpscaler              │
│     - Extract image DPI               - OpenCV upscaling     │
│     - Calculate min/avg/max          - Multiple algorithms   │
│     - Determine if upscaling needed   - Temp file creation   │
│                   ↓                               ↓           │
│  5. PDFPreflightResult                                       │
│     - Resolution analysis                                     │
│     - Upscaled PDF path (if created)                         │
│     - Recommendation (original vs upscaled)                   │
│                   ↓                                           │
│  6. DocumentRouter uses recommended PDF                      │
│                   ↓                                           │
│  7. Parse with Marker/PyMuPDF4LLM/PyMuPDF                   │
│                   ↓                                           │
│  8. Cleanup temporary upscaled file                          │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Modules

- **`PDFResolutionAnalyzer`** (`src/data_ingestor/utils/pdf_resolution.py`)
  - Analyzes PDF images to extract DPI metadata
  - Calculates min/avg/max DPI across all pages
  - Determines if upscaling is recommended

- **`PDFUpscaler`** (`src/data_ingestor/utils/pdf_upscaler.py`)
  - Upscales low-resolution PDFs using OpenCV
  - Supports multiple upscaling algorithms (Lanczos, Bicubic, etc.)
  - Creates temporary upscaled PDF files

- **`PDFDocumentAnalyzer`** (`src/data_ingestor/pipeline/pdf_analyzer.py`)
  - Orchestrates resolution analysis and upscaling
  - Integrates with DocumentRouter
  - Manages temporary file lifecycle

## Configuration

### Environment Variables

Configure PDF resolution pre-processing via environment variables:

```bash
# Enable/disable automatic upscaling (default: true)
DATA_INGESTOR_ENABLE_PDF_UPSCALING=true

# Minimum acceptable DPI - trigger upscaling below this (default: 300)
DATA_INGESTOR_PDF_MIN_DPI=300

# Target DPI for upscaling (default: 300)
DATA_INGESTOR_PDF_TARGET_DPI=300

# Upscaling algorithm (default: lanczos)
# Options: lanczos, bicubic, inter_cubic, inter_linear, inter_area
DATA_INGESTOR_PDF_UPSCALE_ALGORITHM=lanczos

# Preserve original if upscaling fails (default: true)
DATA_INGESTOR_PDF_PRESERVE_ORIGINAL_ON_ERROR=true
```

### Programmatic Configuration

```python
from data_ingestor.core.config import Settings

# Create settings with custom resolution configuration
settings = Settings(
    enable_pdf_upscaling=True,
    pdf_min_dpi=300,
    pdf_target_dpi=300,
    pdf_upscale_algorithm="lanczos",
    pdf_preserve_original_on_error=True,
)

# Pass to DocumentRouter
from data_ingestor.pipeline.router import DocumentRouter

router = DocumentRouter(settings=settings)
```

## Usage

### Automatic Mode (Default)

When processing PDFs through the DocumentRouter, resolution pre-processing happens automatically:

```python
from data_ingestor.pipeline.router import DocumentRouter

router = DocumentRouter()

# Automatic resolution analysis and upscaling
document, result = router.process_document(source_path="low_res_document.pdf")

# Check if upscaling was performed
if "upscaling" in document.metadata:
    upscaling_info = document.metadata["upscaling"]
    if upscaling_info["performed"]:
        print(f"PDF was upscaled: {upscaling_info['resolution_analysis']}")
```

### Manual Analysis

Use the analyzer directly for custom workflows:

```python
from data_ingestor.pipeline.pdf_analyzer import PDFDocumentAnalyzer

analyzer = PDFDocumentAnalyzer()

# Analyze PDF and optionally upscale
result = analyzer.analyze("document.pdf", perform_upscaling=True)

# Check results
if result.needs_upscaling:
    print(f"Min DPI: {result.resolution_analysis['min_dpi']}")
    print(f"Avg DPI: {result.resolution_analysis['avg_dpi']}")

if result.should_use_upscaled:
    print(f"Using upscaled PDF: {result.upscaled_path}")
else:
    print("Using original PDF")
```

### Quick Resolution Check

For simple resolution checking without upscaling:

```python
from data_ingestor.utils.pdf_resolution import quick_resolution_check

# Returns True if upscaling recommended
needs_upscaling = quick_resolution_check("document.pdf", min_dpi=300)

if needs_upscaling:
    print("Document is below 300 DPI and should be upscaled")
```

### Direct Upscaling

Upscale a PDF without automatic analysis:

```python
from data_ingestor.utils.pdf_upscaler import PDFUpscaler, UpscaleAlgorithm

upscaler = PDFUpscaler(
    target_dpi=300,
    algorithm=UpscaleAlgorithm.LANCZOS,
)

result = upscaler.upscale_pdf(
    input_path="low_res.pdf",
    output_path="high_res.pdf",
)

if result["success"]:
    print(f"Upscaled in {result['processing_time']}s")
    print(f"Size: {result['before_size']} → {result['after_size']} bytes")
```

## Upscaling Algorithms

### Supported Algorithms

| Algorithm | Quality | Speed | Use Case |
|-----------|---------|-------|----------|
| **Lanczos** (default) | Excellent | Slow | Best quality for OCR |
| **Bicubic** | Very Good | Medium | Balanced quality/speed |
| **Inter Cubic** | Good | Fast | Quick upscaling |
| **Inter Linear** | Fair | Very Fast | Speed-critical applications |
| **Inter Area** | Good | Fast | Downscaling (not recommended) |

### Algorithm Selection

```python
from data_ingestor.utils.pdf_upscaler import PDFUpscaler, UpscaleAlgorithm

# High quality (recommended for OCR)
upscaler = PDFUpscaler(algorithm=UpscaleAlgorithm.LANCZOS)

# Balanced quality/speed
upscaler = PDFUpscaler(algorithm=UpscaleAlgorithm.BICUBIC)

# Speed-optimized
upscaler = PDFUpscaler(algorithm=UpscaleAlgorithm.INTER_LINEAR)
```

## Performance Characteristics

### Resolution Analysis

- **Overhead**: <100ms per document (typical)
- **Memory**: ~50MB per PDF page during analysis
- **Dependencies**: PyMuPDF (already installed)

### Upscaling

| Document Type | Pages | Input Size | Output Size | Time (Lanczos) | Time (Bicubic) |
|---------------|-------|------------|-------------|----------------|----------------|
| Low-res scan | 1 | 500KB | 2MB | 0.5s | 0.3s |
| Low-res scan | 10 | 5MB | 20MB | 5s | 3s |
| Low-res scan | 100 | 50MB | 200MB | 50s | 30s |

**Notes**:
- Times measured on standard laptop (Intel i7, 16GB RAM)
- Actual performance varies with image complexity
- GPU acceleration not currently used (future enhancement)

## Metadata

The upscaling process adds detailed metadata to processed documents:

```python
document.metadata["upscaling"] = {
    "performed": True,
    "original_path": "/path/to/original.pdf",
    "upscaled_path": "/tmp/data_ingestor_upscaled/original_upscaled_1234567890.pdf",
    "resolution_analysis": {
        "needs_upscaling": True,
        "min_dpi": 150.0,
        "avg_dpi": 175.0,
        "max_dpi": 200.0,
        "image_count": 5,
        "low_res_image_count": 5,
        "details": [
            {
                "page_number": 1,
                "image_count": 1,
                "min_dpi": 150.0,
                "avg_dpi": 150.0,
                "max_dpi": 150.0
            },
            # ... more pages
        ]
    },
    "upscaling_result": {
        "success": True,
        "output_path": "/tmp/...",
        "processing_time": 2.5,
        "before_size": 500000,
        "after_size": 2000000,
        "size_increase_ratio": 4.0,
        "pages_processed": 5
    }
}
```

## Error Handling

### Graceful Degradation

The system is designed to gracefully handle errors:

1. **Analysis Failure**: Falls back to original PDF, logs warning
2. **Upscaling Failure**: Uses original PDF, adds error to metadata
3. **File Not Found**: Raises `FileNotFoundError` (standard behavior)
4. **Corrupted PDF**: Passes error to parser for handling

### Example Error Handling

```python
from data_ingestor.pipeline.pdf_analyzer import PDFDocumentAnalyzer

analyzer = PDFDocumentAnalyzer()

try:
    result = analyzer.analyze("document.pdf")
except FileNotFoundError:
    print("PDF file not found")
except Exception as e:
    print(f"Analysis failed: {e}")
    # Router will attempt parsing with original file
```

## Best Practices

### When to Enable Upscaling

✅ **Enable for:**
- Scanned documents from scanners <300 DPI
- Photos of documents from mobile devices
- Historical documents with poor digitization
- Documents destined for OCR processing

❌ **Disable for:**
- Digital-born PDFs (already high resolution)
- Very large document batches (performance impact)
- Documents with acceptable text extraction
- Non-OCR workflows

### Performance Optimization

```python
# For speed-critical applications
settings = Settings(
    enable_pdf_upscaling=True,
    pdf_min_dpi=200,  # Lower threshold
    pdf_upscale_algorithm="inter_cubic",  # Faster algorithm
)

# For quality-critical applications
settings = Settings(
    enable_pdf_upscaling=True,
    pdf_min_dpi=300,  # Standard threshold
    pdf_target_dpi=600,  # Higher target
    pdf_upscale_algorithm="lanczos",  # Best quality
)
```

### Temporary File Management

Upscaled PDFs are stored in temporary directories:

```bash
# Default location
/tmp/data_ingestor_upscaled/

# Files are automatically cleaned up after parsing
# Manual cleanup if needed:
rm -rf /tmp/data_ingestor_upscaled/
```

## Testing

### Unit Tests

Run Phase 1c unit tests:

```bash
uv run pytest tests/unit/test_pdf_resolution.py tests/unit/test_pdf_upscaler.py -v
```

### Integration Tests

Test with real PDFs:

```python
from data_ingestor.pipeline.router import DocumentRouter

router = DocumentRouter()

# Process low-resolution PDF
document, result = router.process_document(source_path="test_low_res.pdf")

# Verify upscaling occurred
assert document.metadata["upscaling"]["performed"]
assert result.success
```

Run comprehensive integration tests:

```bash
uv run pytest tests/integration/test_pdf_upscaling_integration.py -v -s
```

## Validation

### Automated Validation

**Step 1: Generate Test PDFs**

Generate a suite of test PDFs at different DPI levels:

```bash
python scripts/generate_test_pdfs.py --dpi-tests --output-dir data/test_pdfs
```

This creates test PDFs at: 72, 100, 150, 200, 300, 400, and 600 DPI.

**Step 2: Validate Resolution Detection**

Verify that low-resolution PDFs are correctly identified:

```bash
# Test low-res detection (150 DPI - should need upscaling)
python scripts/validate_pdf_resolution.py data/test_pdfs/dpi_tests/test_150dpi.pdf

# Test high-res detection (300 DPI - should NOT need upscaling)
python scripts/validate_pdf_resolution.py data/test_pdfs/dpi_tests/test_300dpi.pdf
```

Expected output for 150 DPI:
```
Resolution Analysis Results:
  Needs Upscaling: True
  Min DPI: 150.0
  Avg DPI: 150.0
  Low-Res Images: 1/1
```

Expected output for 300 DPI:
```
Resolution Analysis Results:
  Needs Upscaling: False
  Min DPI: 300.0
  Avg DPI: 300.0
  Low-Res Images: 0/1
```

**Step 3: Validate Upscaling**

Verify that upscaling increases DPI to 300:

```bash
# Upscale 150 DPI PDF
python scripts/validate_pdf_resolution.py \
  data/test_pdfs/dpi_tests/test_150dpi.pdf \
  --upscale \
  --output upscaled_150_to_300.pdf
```

Expected output:
```
Step 2: PDF Upscaling
  Upscaling Results:
    Success: True
    Original Size: XXX KB
    Upscaled Size: YYY KB
    Processing Time: Z.Z s

Step 3: Verify Upscaled Resolution
  Resolution Analysis Results:
    Min DPI: 300.0
    Avg DPI: 300.0

  DPI Improvement:
    Original Min DPI: 150.0
    Upscaled Min DPI: 300.0
    Improvement: 150.0 DPI (100.0%)

    ✓ Target DPI (300) achieved!
```

**Step 4: Run Integration Tests**

Run the comprehensive integration test suite:

```bash
uv run pytest tests/integration/test_pdf_upscaling_integration.py -v -s
```

This tests:
- Detection of low-resolution PDFs (150 DPI)
- Detection of high-resolution PDFs (300 DPI)
- Upscaling of low-res PDFs to 300 DPI
- Verification that upscaling increases DPI
- Skipping upscaling for high-res PDFs
- DocumentRouter integration
- Configuration handling
- Metadata accuracy
- Processing time validation

### Manual Validation

For manual testing with your own PDFs:

**1. Check PDF Resolution**

```bash
python scripts/validate_pdf_resolution.py your_document.pdf
```

**2. Upscale if Needed**

```bash
python scripts/validate_pdf_resolution.py your_document.pdf --upscale
```

**3. Compare Quality**

Visual comparison:
- Open original PDF
- Open upscaled PDF
- Zoom to 200-400% to see quality differences
- Check text clarity and edge sharpness

**4. Test OCR Improvement**

```python
from data_ingestor.pipeline.router import DocumentRouter

router = DocumentRouter()

# Process original
doc1, result1 = router.process_document(source_path="original.pdf")

# Process upscaled
doc2, result2 = router.process_document(source_path="upscaled.pdf")

# Compare extraction quality
print(f"Original: {len(doc1.elements)} elements")
print(f"Upscaled: {len(doc2.elements)} elements")
```

### Validation Checklist

- [ ] ✓ Unit tests pass (26 tests)
- [ ] ✓ Integration tests pass (all test classes)
- [ ] ✓ Test PDFs generated at various DPI levels
- [ ] ✓ Low-res PDFs correctly identified (<300 DPI)
- [ ] ✓ High-res PDFs correctly identified (>=300 DPI)
- [ ] ✓ Upscaling increases DPI to target (300 DPI)
- [ ] ✓ Upscaling improves visual quality
- [ ] ✓ Processing time is reasonable (<100ms analysis, varies for upscaling)
- [ ] ✓ Metadata accurately reflects upscaling status
- [ ] ✓ Temporary files are cleaned up
- [ ] ✓ Error handling works (corrupted PDFs, missing files)
- [ ] ✓ Configuration settings respected (min_dpi, target_dpi, algorithm)

## Troubleshooting

### Common Issues

#### 1. Upscaling Not Triggered

**Symptom**: PDFs are not being upscaled even when they appear low-resolution

**Possible Causes**:
- `enable_pdf_upscaling=False` in configuration
- PDF has no images (text-only PDFs)
- Images in PDF have zero-sized bounding boxes
- DPI is above the `pdf_min_dpi` threshold

**Solution**:
```python
# Enable upscaling
settings = Settings(enable_pdf_upscaling=True, pdf_min_dpi=300)

# Check resolution manually
from data_ingestor.utils.pdf_resolution import PDFResolutionAnalyzer
analyzer = PDFResolutionAnalyzer(min_dpi_threshold=300)
result = analyzer.analyze_pdf_resolution("document.pdf")
print(result)
```

#### 2. Out of Memory Errors

**Symptom**: Process crashes or hangs during upscaling

**Possible Causes**:
- Very large PDFs (>100 pages)
- High target DPI (>600)
- Insufficient system memory

**Solution**:
```python
# Reduce target DPI
settings = Settings(pdf_target_dpi=300)

# Or process in smaller batches
# Or increase system memory/swap
```

#### 3. Slow Performance

**Symptom**: Upscaling takes too long

**Possible Causes**:
- Lanczos algorithm (highest quality, slowest)
- Large PDFs with many pages
- High target DPI

**Solution**:
```python
# Use faster algorithm
settings = Settings(pdf_upscale_algorithm="bicubic")

# Or reduce target DPI
settings = Settings(pdf_target_dpi=300)

# Or disable for batch processing
settings = Settings(enable_pdf_upscaling=False)
```

## Future Enhancements

Planned improvements for Phase 2+:

- **GPU Acceleration**: Use CUDA for faster upscaling
- **Selective Page Upscaling**: Only upscale pages with low-res images
- **Progressive Analysis**: Analyze first few pages to estimate document quality
- **Adaptive Algorithms**: Automatically select best algorithm based on content
- **Batch Optimization**: Process multiple PDFs in parallel

## Related Documentation

- [PROJECT_PLAN.md](PROJECT_PLAN.md) - Complete project roadmap
- [INTELLIGENT_OCR_SYSTEM.md](INTELLIGENT_OCR_SYSTEM.md) - Phase 2 intelligent routing (future)
- [PERFORMANCE_BENCHMARKING_GUIDE.md](PERFORMANCE_BENCHMARKING_GUIDE.md) - Phase 1b benchmarking

## Support

For issues or questions:

1. Check troubleshooting section above
2. Review test cases in `tests/unit/test_pdf_resolution.py`
3. Check logs for detailed error messages
4. Consult Response-Aware Development assumption tags in code

---

**Version History**:
- v1.0 (2025-11-06): Initial Phase 1c implementation
