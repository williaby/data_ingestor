# Fuzzing Harnesses for Data Ingestor

This directory contains fuzzing harnesses for continuous security testing of the Data Ingestor document
processing pipeline using [ClusterFuzzLite](https://google.github.io/clusterfuzzlite/) and
[Atheris](https://github.com/google/atheris).

## Overview

Fuzzing is an automated testing technique that provides random/malformed inputs to detect crashes, hangs,
memory corruption, and unexpected behavior. These harnesses run continuously in CI/CD to catch security
vulnerabilities and edge cases.

## Fuzzing Harnesses

### 1. `fuzz_pdf_parser.py`

**Target**: PyMuPDF-based PDF parsers ([src/data_ingestor/parsers/pdf_parser.py](../src/data_ingestor/parsers/pdf_parser.py))

**Test Areas**:
- PDF parsing and validation
- Text extraction from malformed PDFs
- Metadata extraction
- Block processing
- Error handling for corrupted/password-protected PDFs
- Memory management for large PDFs

**Key Risks Tested**:
- Buffer overflows in PDF parsing
- Infinite loops in malformed PDF structures
- Memory exhaustion from crafted PDFs
- Crashes from unexpected PDF features

### 2. `fuzz_document_router.py`

**Target**: DocumentRouter and format detection ([src/data_ingestor/pipeline/router.py](../src/data_ingestor/pipeline/router.py))

**Test Areas**:
- Format detection (libmagic, mimetypes, extension fallback)
- Parser selection and fallback chains
- Deduplication logic
- Hash computation
- Error handling for unsupported formats

**Key Risks Tested**:
- Format detection bypass/confusion
- Hash collision handling
- Parser fallback infinite loops
- Resource exhaustion from deduplication cache

### 3. `fuzz_chunker.py`

**Target**: TokenChunker and ByTitleChunker ([src/data_ingestor/chunking/](../src/data_ingestor/chunking/))

**Test Areas**:
- Token counting with tiktoken
- Chunk overlap logic
- Table preservation
- Section-aware chunking
- Boundary detection
- Memory management for large documents

**Key Risks Tested**:
- Token counting edge cases
- Overlap boundary errors
- Infinite loops in chunk splitting
- Memory exhaustion from adversarial document structures

## Running Fuzzers Locally

### Prerequisites

```bash
# Install Atheris (Python 3.8-3.11 required)
pip install atheris

# Install project dependencies
uv sync --no-group dev
```

### Run Individual Fuzzer

```bash
# Run PDF parser fuzzer for 60 seconds
python fuzz/fuzz_pdf_parser.py -atheris_runs=1000000

# Run document router fuzzer with custom timeout
python fuzz/fuzz_document_router.py -max_total_time=300

# Run chunker fuzzer with specific seed corpus
python fuzz/fuzz_chunker.py -atheris_runs=500000
```

### Run with Coverage-Guided Fuzzing

```bash
# Generate coverage report while fuzzing
python fuzz/fuzz_pdf_parser.py -atheris_runs=100000 \
    -print_pcs=1 \
    -print_coverage=1
```

## CI/CD Integration

Fuzzing runs automatically on every push and pull request via
[`.github/workflows/cifuzzy.yml`](../.github/workflows/cifuzzy.yml).

**Workflow Configuration**:
- **Fuzz Duration**: 600 seconds (10 minutes) per PR/commit
- **Sanitizer**: AddressSanitizer (detects memory errors)
- **Output**: SARIF reports uploaded to GitHub Security
- **Artifacts**: Crash inputs saved for 7 days

**On Failure**:
1. Workflow marks PR as failing
2. Crash artifacts uploaded to GitHub Actions artifacts
3. SARIF report uploaded to Security tab
4. Developers investigate crash input and fix root cause

## Understanding Fuzzing Results

### Successful Run
```
INFO: Running with entropic power schedule (0xFF, 100).
INFO: Seed: 1234567890
INFO: -max_len is not provided; libFuzzer will not generate inputs larger than 4096 bytes
INFO: A corpus is not provided, starting from an empty corpus
#2      INITED cov: 123 ft: 456 corp: 1/1b exec/s: 0 rss: 45Mb
#1000   NEW    cov: 145 ft: 567 corp: 12/789b lim: 4096 exec/s: 500 rss: 67Mb
```

**Key Metrics**:
- `cov`: Code coverage (higher is better)
- `ft`: Feature coverage (unique execution paths)
- `corp`: Corpus size (interesting test cases)
- `exec/s`: Executions per second (speed)
- `rss`: Memory usage

### Crash Found
```
==1234==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x...
    #0 0x... in TestOneInput fuzz/fuzz_pdf_parser.py:42
    #1 0x... in PyMuPDFParser.parse src/data_ingestor/parsers/pdf_parser.py:67

SUMMARY: AddressSanitizer: heap-buffer-overflow
```

**Action Required**:
1. Download crash input from GitHub Actions artifacts
2. Reproduce locally: `python fuzz/fuzz_pdf_parser.py crash-input-file`
3. Debug and fix root cause in source code
4. Verify fix: Re-run fuzzer with crash input (should not crash)

## Best Practices

### Writing Fuzzing Harnesses

1. **Handle All Exceptions**: Fuzzers must catch all exceptions to avoid false positives
   ```python
   try:
       result = parser.parse(document)
   except Exception:  # nosec B110
       # Expected for malformed inputs
       pass
   ```

2. **Limit Execution Time**: Prevent infinite loops by limiting iterations
   ```python
   for element in result.elements[:5]:  # Limit to first 5 elements
       _ = element.content
   ```

3. **Use Atheris Instrumentation**: Wrap imports for coverage-guided fuzzing
   ```python
   with atheris.instrument_imports():
       from data_ingestor.parsers.pdf_parser import PyMuPDFParser
   ```

4. **Clean Up Resources**: Always clean up temporary files/resources
   ```python
   try:
       # Fuzzing logic
   finally:
       if tmp_path.exists():
           tmp_path.unlink()
   ```

### Interpreting Results

**Not a Bug**:
- Expected exceptions for invalid inputs
- Graceful error handling
- Logged warnings

**Potential Bug**:
- Uncaught exceptions
- Segmentation faults
- Memory leaks
- Infinite loops
- Resource exhaustion

## Python Version Compatibility

**Atheris Requirement**: Python 3.8 - 3.11 only

**Why not Python 3.12+?**
Atheris native code doesn't support PRECALL opcode changes introduced in Python 3.12. The fuzzing workflow
uses Python 3.11.13 (provided by ClusterFuzzLite base image).

**Local Development**:
```bash
# Verify Python version
python3 --version  # Should be 3.8-3.11

# If using 3.12+, create 3.11 environment
pyenv install 3.11.13
pyenv local 3.11.13
```

## Additional Resources

- [ClusterFuzzLite Documentation](https://google.github.io/clusterfuzzlite/)
- [Atheris Documentation](https://github.com/google/atheris)
- [OSS-Fuzz Python Integration](https://google.github.io/oss-fuzz/getting-started/new-project-guide/python-lang/)
- [AddressSanitizer Documentation](https://github.com/google/sanitizers/wiki/AddressSanitizer)

## Troubleshooting

### Fuzzer Fails to Build

**Error**: `ImportError: No module named 'atheris'`

**Solution**:
```bash
pip install atheris
# Verify Python 3.8-3.11
python3 --version
```

### Fuzzer Hangs

**Cause**: Infinite loop in target code

**Solution**:
```bash
# Run with timeout
timeout 60s python fuzz/fuzz_pdf_parser.py
```

### Low Coverage

**Cause**: Limited seed corpus or fuzzer not finding interesting inputs

**Solution**:
```bash
# Increase fuzzing duration
python fuzz/fuzz_pdf_parser.py -max_total_time=600

# Provide seed corpus directory
python fuzz/fuzz_pdf_parser.py corpus_dir/
```

---

**Maintained by**: Data Ingestor Security Team
**Last Updated**: 2025-11-07
**CI Status**: [![ClusterFuzzLite](../../.github/workflows/cifuzzy.yml/badge.svg)](../../.github/workflows/cifuzzy.yml)
