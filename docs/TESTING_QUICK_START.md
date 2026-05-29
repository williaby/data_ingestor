# Testing Quick Start Guide

## ✅ What You Asked For

**Question**: "Is there a way to test the test_cli_integration.py without needing marker to make sure we have the code correct? Then during PRs to main we would test with marker?"

**Answer**: YES! We now have a **two-tier testing strategy** that does exactly this.

## 🚀 Quick Commands

### Local Development (Fast - No Marker Required)

```bash
# Run in VS Code Test Explorer (already configured) ✅
# OR manually:
SKIP_MARKER_PARSER=1 uv run pytest tests/ -m 'not slow'

# Result: 660+ tests in ~35 seconds
# Tests: Code correctness, structure, basic functionality
```

### PR to Main (Comprehensive - With Marker)

```bash
# Full test suite with quality validation
uv run pytest tests/

# Result: 660+ tests in ~2-5 minutes
# Tests: Everything + parsing accuracy, content quality
```

## 📋 Test Breakdown

### Tests That Run Locally (Without Marker)

✅ **test_process_command_with_real_pdf** - Basic PDF processing
✅ **test_process_command_markdown_output** - Markdown export
✅ **test_process_command_both_formats** - Dual format export
✅ **test_process_command_basic_validation** - Structure validation
⏭️ **test_process_command_quality_validation** - SKIPPED (needs Marker)

**Result**: 4 passed, 1 skipped in 0.34s ⚡

### Tests That Run in CI/PR (With Marker)

✅ **All of the above** +
✅ **test_process_command_quality_validation** - Content accuracy
✅ **Other quality-dependent tests** - High-fidelity parsing

**Result**: 5 passed in ~15s (with Marker initialization)

## 🎯 How It Works

### 1. Basic Validation (Local Development)

```python
def test_process_command_basic_validation(self, cli_runner, sample_pdf_paths, tmp_path):
    """Tests code correctness without Marker."""

    # What it validates:
    # ✅ CLI command executes successfully
    # ✅ Output file is created
    # ✅ JSON structure is valid
    # ✅ Required fields exist
    # ✅ Content is extracted
    # ✅ Parser was used (any of: PyMuPDF, PyMuPDF4LLM, Marker)
```

**This test ensures your code logic works correctly!**

### 2. Quality Validation (CI/PR Only)

```python
@pytest.mark.requires_marker
def test_process_command_quality_validation(self, cli_runner, sample_pdf_paths, ...):
    """Tests parsing accuracy with Marker."""

    if os.getenv("SKIP_MARKER_PARSER") == "1":
        pytest.skip("Quality validation requires Marker parser - run in CI/PR")

    # What it validates:
    # ✅ Accurate title extraction
    # ✅ Precise content matching
    # ✅ High-quality text extraction
```

**This test ensures production-quality output!**

## 🔧 VS Code Configuration

Already configured in [.vscode/settings.json](../.vscode/settings.json):

```json
{
  "python.testing.pytestEnv": {
    "SKIP_MARKER_PARSER": "1"  // Automatically skips Marker
  }
}
```

Just open VS Code Test Explorer and run tests - it works automatically! 🎉

## 📊 Real Results

### Before (With Marker Loading)
- **Time**: 10+ seconds per test (hanging/timeout)
- **Memory**: OOM crashes with parallel execution
- **Developer Experience**: 😫 Frustrating

### After (Two-Tier Strategy)
- **Tier 1 (Local)**: 0.34s per test class ⚡
- **Tier 2 (CI/PR)**: Full validation with Marker ✅
- **Developer Experience**: 😊 Happy coding!

## 🎓 Example Workflow

### Developer Workflow

```bash
# 1. Make code changes
vim src/data_ingestor/cli/main.py

# 2. Run tests in VS Code Test Explorer
# Click "Run Tests" button
# Result: 4 passed, 1 skipped in 0.34s ✅

# 3. Commit and push
git add .
git commit -m "feat: improve CLI error handling"
git push origin feature/my-changes
```

### CI/PR Workflow

```yaml
# GitHub Actions automatically runs:
1. Tier 1 tests (fast validation) on every push
2. Tier 2 tests (with Marker) on PRs to main

# If Tier 2 fails:
#   - Parsing quality issue detected
#   - Fix before merge to main
```

## 💡 Key Benefits

✅ **Fast Development**: No waiting for Marker to load
✅ **Code Correctness**: Validates logic works
✅ **Production Quality**: Marker validates accuracy in CI
✅ **No GPU Required**: Develop on any machine
✅ **Merge Confidence**: Quality gate before main

## 📚 More Details

See [TESTING_STRATEGY.md](TESTING_STRATEGY.md) for:
- Complete marker documentation
- CI/CD configuration examples
- Test migration guide
- Advanced usage patterns

---

**TL;DR**: Your code is validated locally in ~35s without Marker. Production quality is validated in CI/PR with Marker. Best of both worlds! 🎉
