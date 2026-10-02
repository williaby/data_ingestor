# Marker LLM Integration - Free Tier POC

## Status: ✅ Ready for Testing

The Marker LLM integration with OpenRouter (free tier) is now implemented and ready for testing!

## What Was Implemented

### 1. ✅ MarkerParser Enhancement
- Added LLM configuration to existing [MarkerParser](../src/data_ingestor/parsers/pdf_parser.py#L349)
- Integrated OpenRouter via OpenAI-compatible endpoint
- Configuration via environment variables
- Automatic fallback to basic Marker if LLM disabled

### 2. ✅ Environment Configuration
- Created [.env.example](../.env.example) with configuration template
- Free tier model as default (zero cost)
- `.env` already in `.gitignore` (your API keys are safe)

### 3. ✅ Test Scripts
- Enhanced [run_pdf_tests.py](../scripts/run_pdf_tests.py) with LLM status display
- Created [test_marker_llm.py](../scripts/test_marker_llm.py) for quick manual testing

### 4. ✅ Documentation
- [POC Setup Guide](MARKER_LLM_SETUP_POC.md) - Quick start instructions
- [Full Integration Guide](MARKER_LLM_INTEGRATION.md) - Complete cost-benefit analysis
- [Implementation Guide](MARKER_LLM_IMPLEMENTATION_GUIDE.md) - Production implementation

## Quick Start (3 steps)

### Step 1: Configure Environment

```bash
cd /home/byron/dev/data_ingestor

# Copy environment template
cp .env.example .env

# Edit and add your OpenRouter API key (from zen-mcp-server)
nano .env
```

Add these two lines to `.env`:
```bash
MARKER_USE_LLM=true
OPENROUTER_API_KEY=your_key_from_zen_server
```

### Step 2: Verify Installation

```bash
# Ensure advanced-pdf group is installed
uv sync --extra advanced-pdf

# Quick check
uv run python -c "import marker; print('Marker installed')"
```

### Step 3: Test!

```bash
# Quick test with sample PDF
uv run python scripts/test_marker_llm.py

# Or run full test suite
uv run python scripts/run_pdf_tests.py
```

## What LLM Enhancement Provides

When `MARKER_USE_LLM=true`, you get:

✅ **Better table extraction** - Tables that span multiple pages are merged intelligently
✅ **Improved math formatting** - Mathematical expressions are better formatted
✅ **Form value extraction** - Data from PDF forms is extracted more accurately
✅ **Complex layout handling** - Multi-column documents work better

## Free Tier Models (Zero Cost)

The POC uses **free tier models** from OpenRouter:

| Model | Best For |
|-------|----------|
| `meta-llama/llama-3.1-405b-instruct:free` | General purpose (DEFAULT) |
| `qwen/qwen-2.5-coder-32b-instruct:free` | Technical/code-heavy PDFs |
| `deepseek/deepseek-r1-distill-llama-70b:free` | Complex reasoning |
| `qwen/qwen2.5-vl-72b-instruct:free` | Image-heavy PDFs |

**Cost**: $0/month for unlimited documents!

## Test Output

When you run tests, you'll see:

```
Initializing PDF parsers...
✓ Registered MarkerParser (priority 10)
  LLM Enhancement: ENABLED
  Model: meta-llama/llama-3.1-405b-instruct:free
  Cost: FREE (zero cost per document)

Processing sample.pdf...
  Extracted 1,234 words from 5 pages (45 elements) [MarkerParser] ✨ LLM
```

The `✨ LLM` indicator shows LLM enhancement was used.

## Troubleshooting

### "OPENROUTER_API_KEY not found"

Your API key isn't set. Check your `.env` file:

```bash
# Verify .env exists and has the key
cat .env | grep OPENROUTER_API_KEY

# If missing, get it from zen-mcp-server
cat /home/byron/dev/zen-mcp-server/.env | grep OPENROUTER_API_KEY
```

### "marker-pdf not installed"

```bash
uv sync --extra advanced-pdf
```

### LLM seems slow

Free tier models may be slower than paid models:
- Expected: 5-15 seconds per page
- If too slow, consider upgrading to economy tier (Gemini Flash @ $0.0026/10 pages)

### No improvement visible

Try a more complex PDF:
- Multi-page tables
- Mathematical formulas
- Multi-column layouts
- PDF forms

Simple text-only PDFs won't show much difference.

## Files Modified

1. [`src/data_ingestor/parsers/pdf_parser.py`](../src/data_ingestor/parsers/pdf_parser.py) - Added LLM configuration
2. [`scripts/run_pdf_tests.py`](../scripts/run_pdf_tests.py) - Enhanced with LLM display
3. [`.env.example`](../.env.example) - Created configuration template
4. [`scripts/test_marker_llm.py`](../scripts/test_marker_llm.py) - Created quick test script

## Next Steps

### 1. Validate Quality

Test with your actual PDFs:

```bash
# Test a specific PDF
uv run python scripts/test_marker_llm.py path/to/your.pdf

# Compare with and without LLM
MARKER_USE_LLM=false uv run python scripts/test_marker_llm.py your.pdf
MARKER_USE_LLM=true uv run python scripts/test_marker_llm.py your.pdf
```

### 2. Try Different Models

```bash
# Technical documents
MARKER_LLM_MODEL=qwen/qwen-2.5-coder-32b-instruct:free uv run python scripts/test_marker_llm.py

# Image-heavy PDFs
MARKER_LLM_MODEL=qwen/qwen2.5-vl-72b-instruct:free uv run python scripts/test_marker_llm.py
```

### 3. Consider Upgrades

If you need better performance/quality, see:
- [Cost-benefit analysis](MARKER_LLM_INTEGRATION.md#cost-benefit-analysis-zen-models-for-marker)
- Economy tier: Gemini Flash @ $0.0026/10 pages (2-3x faster)
- Premium tier: GPT-5 @ $0.07/10 pages (best quality)

## Documentation

- **[POC Setup Guide](MARKER_LLM_SETUP_POC.md)** ← Start here!
- [Full Integration Analysis](MARKER_LLM_INTEGRATION.md) - Cost-benefit for all 24 zen models
- [Implementation Guide](MARKER_LLM_IMPLEMENTATION_GUIDE.md) - Production code & features

## Support

- **Marker issues**: [GitHub](https://github.com/VikParuchuri/marker)
- **OpenRouter API**: [Docs](https://openrouter.ai/docs)
- **Zen models**: See your `zen-mcp-server/docs/models/current-models.md`

---

**Ready to test?** → See [MARKER_LLM_SETUP_POC.md](MARKER_LLM_SETUP_POC.md)

**Implementation Date**: 2025-11-03
**Status**: Free Tier POC - Ready for Testing
**Cost**: $0/month (free tier models)
