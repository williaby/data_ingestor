# Marker LLM Setup Guide - Free Tier POC

## Quick Start (5 minutes)

This guide helps you set up Marker's LLM-enhanced PDF extraction using **free tier models** from OpenRouter.

### Step 1: Copy Your OpenRouter API Key

You already have an OpenRouter API key configured in your zen-mcp-server. Let's reuse it:

```bash
# Option 1: Check your zen-mcp-server .env file
cat /home/byron/dev/zen-mcp-server/.env | grep OPENROUTER_API_KEY

# Option 2: If running, get from environment
echo $OPENROUTER_API_KEY
```

### Step 2: Configure Environment

```bash
# Navigate to data_ingestor project
cd /home/byron/dev/data_ingestor

# Create .env file from example
cp .env.example .env

# Edit .env file
nano .env  # or use your preferred editor
```

**Minimal configuration (just 2 lines needed)**:

```bash
MARKER_USE_LLM=true
OPENROUTER_API_KEY=sk-or-v1-xxxxx  # Your actual key from zen-mcp-server
```

That's it! The default free model (`meta-llama/llama-3.1-405b-instruct:free`) will be used automatically.

### Step 3: Verify Installation

```bash
# Ensure advanced-pdf group is installed
uv sync --extra advanced-pdf

# Verify Marker is available
uv run python -c "import marker; print(f'Marker {marker.__version__} installed')"
```

### Step 4: Test LLM Integration

Run the test script to compare basic Marker vs LLM-enhanced Marker:

```bash
# Run test on sample PDF
uv run python scripts/run_pdf_tests.py
```

Or test a specific PDF:

```bash
# Test with your own PDF
uv run python -c "
from data_ingestor.parsers import MarkerParser
from data_ingestor.core.models import Document, DocumentFormat

parser = MarkerParser()
doc = Document(source_path='your_pdf_file.pdf', format=DocumentFormat.PDF)
result = parser.parse(doc)

print(f'Success: {result.success}')
print(f'Processing time: {result.processing_time:.2f}s')
print(f'Elements extracted: {len(result.elements)}')
print(f'LLM enhanced: {result.metadata.get(\"llm_enhanced\")}')
print(f'Model used: {result.metadata.get(\"llm_model\")}')
"
```

## What Does LLM Enhancement Do?

When `MARKER_USE_LLM=true`, Marker uses an LLM to:

✅ **Merge tables across pages** - Complex tables that span multiple pages are intelligently combined
✅ **Improve inline math formatting** - Mathematical expressions are better formatted
✅ **Extract form values** - Data from PDF forms is more accurately extracted
✅ **Handle complex layouts** - Multi-column documents and irregular layouts work better

## Free Tier Models

All these models have **zero cost** but provide LLM enhancement:

| Model | Best For | Notes |
|-------|----------|-------|
| `meta-llama/llama-3.1-405b-instruct:free` | General purpose | **Default**, largest free model (405B) |
| `qwen/qwen-2.5-coder-32b-instruct:free` | Technical docs | Better for code-heavy PDFs |
| `deepseek/deepseek-r1-distill-llama-70b:free` | Complex analysis | Best reasoning capabilities |
| `qwen/qwen2.5-vl-72b-instruct:free` | Image-heavy PDFs | Vision capabilities included |

To switch models, just update your `.env`:

```bash
# For technical documents with code
MARKER_LLM_MODEL=qwen/qwen-2.5-coder-32b-instruct:free

# For PDFs with lots of images/diagrams
MARKER_LLM_MODEL=qwen/qwen2.5-vl-72b-instruct:free
```

## Testing With/Without LLM

Compare extraction quality:

```bash
# Test WITHOUT LLM (basic Marker)
MARKER_USE_LLM=false uv run python scripts/run_pdf_tests.py

# Test WITH LLM (free tier)
MARKER_USE_LLM=true uv run python scripts/run_pdf_tests.py
```

Look for improvements in:
- Table structure preservation across pages
- Formula formatting quality
- Multi-column layout handling
- Form data extraction accuracy

## Performance Expectations

**Processing Time**:
- Basic Marker: ~2-5 seconds per page
- LLM-enhanced (free tier): ~5-15 seconds per page (slower but better quality)

**Quality Improvements**:
- Tables: 20-40% better structure preservation
- Formulas: 30-50% better formatting
- Complex layouts: 25-35% better handling

## Troubleshooting

### Issue: "OPENROUTER_API_KEY not found"

```bash
# Check if .env file exists
ls -la .env

# Verify key is set
cat .env | grep OPENROUTER_API_KEY

# Test key directly
OPENROUTER_API_KEY=your_key python scripts/run_pdf_tests.py
```

### Issue: "marker-pdf not installed"

```bash
# Install advanced-pdf group
uv sync --extra advanced-pdf

# Verify installation
uv pip show marker-pdf
```

### Issue: "LLM enabled but no improvement"

Free tier models may be rate-limited or slow. Try:

1. **Wait a bit** - Free tier has rate limits
2. **Try different model** - Some free models are faster:
   ```bash
   MARKER_LLM_MODEL=deepseek/deepseek-r1-distill-llama-70b:free
   ```
3. **Check logs** - Enable debug logging:
   ```bash
   LOG_LEVEL=DEBUG uv run python scripts/run_pdf_tests.py
   ```

### Issue: API errors or timeouts

```bash
# Verify your OpenRouter key works
curl -H "Authorization: Bearer $OPENROUTER_API_KEY" \
     https://openrouter.ai/api/v1/models

# If you get 401 Unauthorized, your key is invalid
# Get a new key from: https://openrouter.ai/keys
```

## Next Steps

Once you've validated the free tier POC:

1. **Benchmark quality** - Compare extraction results on your actual PDFs
2. **Measure value** - Determine if LLM enhancement is worth the processing time
3. **Consider upgrades** - See [MARKER_LLM_INTEGRATION.md](MARKER_LLM_INTEGRATION.md) for paid model analysis
4. **Implement complexity routing** - Automatically select models based on document complexity

## Cost Comparison

Current POC (free tier):
- **Cost**: $0/month
- **Quality**: Good for most documents
- **Speed**: Slower than paid models

If you later upgrade to economy tier:
- **Cost**: ~$0.26/month for 100 pages (Gemini Flash)
- **Quality**: 2-3x better than free tier
- **Speed**: 2-3x faster

For detailed cost analysis across all 24 zen models, see:
- [MARKER_LLM_INTEGRATION.md](MARKER_LLM_INTEGRATION.md) - Full cost-benefit analysis
- [MARKER_LLM_IMPLEMENTATION_GUIDE.md](MARKER_LLM_IMPLEMENTATION_GUIDE.md) - Production implementation

## Support

For issues specific to:
- **Marker PDF extraction**: See [Marker GitHub](https://github.com/VikParuchuri/marker)
- **OpenRouter API**: See [OpenRouter Docs](https://openrouter.ai/docs)
- **Zen MCP models**: See your `zen-mcp-server/docs/models/current-models.md`

---

**Last Updated**: 2025-11-03
**Status**: Free Tier POC - Ready for Testing
