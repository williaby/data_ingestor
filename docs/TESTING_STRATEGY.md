# Two-Tier Testing Strategy

This project uses a **two-tier testing strategy** to balance fast local development with comprehensive CI/PR validation.

## Overview

### Tier 1: Local/VS Code Testing (Fast - Without Marker)
- **Purpose**: Rapid feedback during development
- **Speed**: ~35 seconds for 660+ tests
- **Coverage**: Code correctness, structure, basic functionality
- **Environment**: `SKIP_MARKER_PARSER=1`

### Tier 2: CI/PR Testing (Comprehensive - With Marker)
- **Purpose**: Production-quality validation before merge
- **Speed**: ~2-5 minutes (includes Marker parser initialization)
- **Coverage**: Parsing quality, content accuracy, GPU features
- **Environment**: Full parser suite including Marker

## Test Markers

### `@pytest.mark.requires_marker`
Tests that **require Marker parser** for high-quality parsing validation:
- Title/heading extraction accuracy
- Formula/table preservation
- Complex layout handling

**Example:**
```python
@pytest.mark.requires_marker
def test_process_command_quality_validation(self, ...):
    """Validates accurate content extraction (requires Marker)."""
    if os.getenv("SKIP_MARKER_PARSER") == "1":
        pytest.skip("Quality validation requires Marker parser - run in CI/PR")
    # ... test implementation
```

### `@pytest.mark.slow`
Tests that are **memory/time intensive**:
- Large dataset processing (10K+ words)
- Benchmark suites
- Performance tests

Automatically excluded in local development and VS Code.

## Running Tests

### Local Development (Fast)

```bash
# VS Code Test Explorer - automatically configured
# Uses: SKIP_MARKER_PARSER=1, -m 'not slow', -n 2

# Or manually:
SKIP_MARKER_PARSER=1 uv run pytest tests/ -m 'not slow'

# Results: ~35s, 660+ tests
```

### CI/PR Validation (Comprehensive)

```bash
# Full test suite with Marker parser
uv run pytest tests/

# Results: ~2-5min, 660+ tests including quality validation
```

### Specific Test Tiers

```bash
# Only basic validation (without Marker)
SKIP_MARKER_PARSER=1 uv run pytest tests/ -m 'not slow and not requires_marker'

# Only quality validation (with Marker)
uv run pytest tests/ -m 'requires_marker'

# Only fast tests (for quick checks)
uv run pytest tests/ -m fast
```

## VS Code Configuration

The project's [.vscode/settings.json](.vscode/settings.json) is pre-configured for Tier 1 testing:

```json
{
  "python.testing.pytestArgs": [
    "tests",
    "-m", "not slow",        // Skip slow tests
    "-n", "2",               // 2 parallel workers (prevents OOM)
    "--maxfail=5"            // Stop after 5 failures
  ],
  "python.testing.pytestEnv": {
    "SKIP_MARKER_PARSER": "1"  // Skip Marker parser loading
  }
}
```

## Example: CLI Validation Tests

### Basic Validation (Tier 1 - Works Without Marker)
```python
def test_process_command_basic_validation(self, cli_runner, sample_pdf_paths, tmp_path):
    """Test CLI output has correct structure (works without Marker)."""
    # Tests:
    # - Command executes successfully
    # - Output file created
    # - JSON structure valid
    # - Basic fields present
    # - Content extracted
```

**Runs in**: Local development, VS Code, CI ✅

### Quality Validation (Tier 2 - Requires Marker)
```python
@pytest.mark.requires_marker
def test_process_command_quality_validation(self, cli_runner, sample_pdf_paths, ...):
    """Test CLI output matches high-quality parsing (requires Marker)."""
    # Tests:
    # - Accurate title extraction
    # - Precise content matching
    # - High-quality text extraction
```

**Runs in**: CI/PR validation only ✅

## CI/CD Configuration

### GitHub Actions Workflow Example

```yaml
name: Tests

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  # Tier 1: Fast tests (always run)
  fast-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install dependencies
        run: |
          uv sync
      - name: Run fast tests
        env:
          SKIP_MARKER_PARSER: "1"
        run: uv run pytest tests/ -m 'not slow' -n auto

  # Tier 2: Comprehensive tests (PRs to main)
  quality-tests:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request' && github.base_ref == 'main'
    steps:
      - uses: actions/checkout@v4
      - name: Install with Marker
        run: |
          uv sync --extra advanced-pdf
      - name: Run comprehensive tests
        run: uv run pytest tests/ -n auto
```

## Benefits

### For Developers
✅ **Fast feedback loop**: ~35s test runs in VS Code
✅ **No GPU required**: Local development works on any machine
✅ **Reduced memory usage**: Parallel execution doesn't OOM
✅ **Code correctness validation**: Ensures logic works

### For CI/PR
✅ **Quality assurance**: Marker validates parsing accuracy
✅ **Production parity**: Tests with real parsing quality
✅ **Comprehensive coverage**: All tests including slow/quality
✅ **Merge confidence**: High-quality code reaches main

## Migration Guide

If you have existing tests that depend on Marker accuracy, convert them to two-tier:

**Before:**
```python
def test_pdf_parsing_validation(self, ...):
    """Test PDF parsing validates content."""
    # Expects high-quality title extraction
    assert "Expected Title" in output
```

**After:**
```python
def test_pdf_parsing_basic(self, ...):
    """Test PDF parsing works (structure validation)."""
    # Tests basic functionality without Marker
    assert len(output["elements"]) > 0
    assert output["parser_used"] in ["PyMuPDFParser", "PyMuPDF4LLMParser", "MarkerParser"]

@pytest.mark.requires_marker
def test_pdf_parsing_quality(self, ...):
    """Test PDF parsing quality (requires Marker)."""
    if os.getenv("SKIP_MARKER_PARSER") == "1":
        pytest.skip("Quality validation requires Marker parser - run in CI/PR")
    # Tests high-quality extraction with Marker
    assert "Expected Title" in output
```

## Summary

| Aspect | Tier 1 (Local) | Tier 2 (CI/PR) |
|--------|---------------|----------------|
| **Environment** | `SKIP_MARKER_PARSER=1` | Full parser suite |
| **Speed** | ~35 seconds | ~2-5 minutes |
| **Tests** | 660+ structural tests | 660+ including quality |
| **Purpose** | Code correctness | Production quality |
| **Runs** | Every save/commit | PR to main |
| **Markers** | `-m 'not slow'` | All tests |

This strategy ensures **fast development cycles** while maintaining **high production quality**.
