# LLM Fallback Mechanism for Marker

**Status:** ✅ Implemented and Ready
**Date:** 2025-11-03

---

## Overview

The Marker parser now supports **intelligent fallback** between free and paid vision models. This ensures:
- ✅ **Zero cost** for normal operations (free tier)
- ✅ **Automatic reliability** when free tier has issues
- ✅ **Transparent operation** with detailed logging
- ✅ **Cost control** through smart fallback logic

---

## How It Works

### Fallback Flow

```
┌─────────────────────────────────────────────────────────────┐
│ PDF Document                                                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │ Try Primary Model     │
         │ (Llama 4 Maverick)    │
         │ FREE                  │
         └───────────┬───────────┘
                     │
                     ├─────── Success ──────┐
                     │                       │
                     │                       ▼
                ✗ API Error          ┌──────────────┐
                     │               │ Return Result│
                     │               │ (Free Model) │
                     ▼               └──────────────┘
         ┌───────────────────────┐
         │ Try Fallback Model    │
         │ (Gemini Flash Lite)   │
         │ PAID (~$0.11/1000pgs) │
         └───────────┬───────────┘
                     │
                     ├─────── Success ──────┐
                     │                       │
                     │                       ▼
                ✗ Error              ┌──────────────┐
                     │               │ Return Result│
                     │               │(Paid Model)  │
                     ▼               └──────────────┘
         ┌───────────────────────┐
         │ Process without LLM   │
         │ (Basic Marker)        │
         └───────────┬───────────┘
                     │
                     ▼
            ┌──────────────┐
            │ Return Result│
            │ (No LLM)     │
            └──────────────┘
```

### When Fallback Triggers

The fallback is **only** triggered for API-related errors:
- ✅ Connection timeout
- ✅ API unavailable (503, 502, 504)
- ✅ Rate limit exceeded (429)
- ✅ Authentication issues (403)
- ✅ Model not found errors
- ❌ **NOT** triggered for: parsing errors, data issues, other exceptions

---

## Configuration

### Environment Variables

Add to your [.env](../.env) file:

```bash
# Enable LLM processing
MARKER_USE_LLM=true

# Primary model (free tier - tried first)
MARKER_LLM_MODEL=meta-llama/llama-4-maverick:free

# Fallback model (paid tier - used if primary fails)
MARKER_LLM_FALLBACK_MODEL=google/gemini-2.5-flash-lite

# Enable automatic fallback (recommended)
MARKER_ENABLE_FALLBACK=true
```

### Configuration Options

#### Primary Model Options

**Recommended (Free):**
```bash
MARKER_LLM_MODEL=meta-llama/llama-4-maverick:free
```

**Alternatives (Free):**
```bash
# Slightly slower but good quality
MARKER_LLM_MODEL=meta-llama/llama-4-scout:free

# Older model, still functional
MARKER_LLM_MODEL=meta-llama/llama-3.1-405b-instruct:free
```

#### Fallback Model Options

**Recommended (Best Value):**
```bash
MARKER_LLM_FALLBACK_MODEL=google/gemini-2.5-flash-lite
# Cost: $0.03/1M input, $0.12/1M output
# ~$0.11 per 1000 pages
```

**Alternative (Premium Quality):**
```bash
MARKER_LLM_FALLBACK_MODEL=google/gemini-2.5-flash
# Cost: $0.075/1M input, $0.30/1M output
# ~$0.28 per 1000 pages
```

**Alternative (Good Quality):**
```bash
MARKER_LLM_FALLBACK_MODEL=google/gemini-2.0-flash-001
# Cost: $0.075/1M input, $0.30/1M output
```

#### Fallback Control

**Enable fallback (default):**
```bash
MARKER_ENABLE_FALLBACK=true
```

**Disable fallback:**
```bash
# Only use primary model, fail if unavailable
MARKER_ENABLE_FALLBACK=false
```

---

## Usage

### Normal Usage (No Code Changes)

The fallback is completely transparent. Just use Marker as normal:

```bash
# CLI usage
uv run python -m data_ingestor.cli process \
  --input data/wind_docs/Where-does-wind-matter.pdf \
  --output test_output/result.json
```

```python
# Python usage
from data_ingestor.parsers.pdf_parser import MarkerParser

parser = MarkerParser()
result = parser.parse("path/to/document.pdf")

# Check which model was used
print(f"Model used: {result.metadata['llm_model']}")
print(f"Fallback triggered: {result.metadata['llm_fallback_used']}")
```

### Logging

The system provides detailed logging:

**Primary Model Success:**
```
INFO - Marker LLM enabled with primary model: meta-llama/llama-4-maverick:free
INFO - Attempting LLM enhancement with primary model: meta-llama/llama-4-maverick:free
INFO - ✓ Successfully processed with primary model: meta-llama/llama-4-maverick:free
```

**Fallback Triggered:**
```
INFO - Marker LLM enabled with primary model: meta-llama/llama-4-maverick:free
INFO - Fallback model configured: google/gemini-2.5-flash-lite
WARNING - Primary model (meta-llama/llama-4-maverick:free) failed with API error: connection timeout
INFO - Attempting fallback to: google/gemini-2.5-flash-lite
INFO - ✓ Successfully processed with fallback model: google/gemini-2.5-flash-lite
```

**Both Models Failed:**
```
WARNING - Primary model (meta-llama/llama-4-maverick:free) failed with API error: connection timeout
INFO - Attempting fallback to: google/gemini-2.5-flash-lite
ERROR - Fallback model also failed: API unavailable
INFO - Processing without LLM enhancement
```

---

## Metadata Tracking

The parser result includes detailed metadata about LLM usage:

```python
{
    "llm_enhanced": true,                                    # Was LLM used?
    "llm_model": "meta-llama/llama-4-maverick:free",        # Which model?
    "llm_fallback_used": false,                             # Was fallback triggered?
    # ... other metadata
}
```

**Example scenarios:**

| Scenario | llm_enhanced | llm_model | llm_fallback_used |
|----------|--------------|-----------|-------------------|
| Primary success | `true` | `meta-llama/llama-4-maverick:free` | `false` |
| Fallback success | `true` | `google/gemini-2.5-flash-lite` | `true` |
| Both failed | `false` | `null` | `false` |
| LLM disabled | `false` | `null` | `false` |

---

## Cost Analysis

### Expected Costs with Fallback

**Scenario 1: Free Model Works 100%**
- Primary model (free): 100% of documents
- Fallback model (paid): 0% of documents
- **Monthly cost: $0**

**Scenario 2: Free Model Works 95%** (realistic)
- Primary model (free): 95% of documents
- Fallback model (paid): 5% of documents
- For 10,000 pages/month:
  - Free: 9,500 pages = $0
  - Paid: 500 pages = ~$0.055
- **Monthly cost: ~$0.06**

**Scenario 3: Free Model Works 80%** (conservative)
- Primary model (free): 80% of documents
- Fallback model (paid): 20% of documents
- For 10,000 pages/month:
  - Free: 8,000 pages = $0
  - Paid: 2,000 pages = ~$0.22
- **Monthly cost: ~$0.22**

**Worst Case: Free Model Completely Unavailable**
- Primary model (free): 0% (all fail)
- Fallback model (paid): 100% of documents
- For 10,000 pages/month:
  - Paid: 10,000 pages = ~$1.10
- **Monthly cost: ~$1.10**

### Cost Comparison

| Configuration | 1K pages | 10K pages | 100K pages |
|---------------|----------|-----------|------------|
| **Free only (no fallback)** | $0 | $0 | $0 |
| **Fallback (95% free)** | $0.006 | $0.06 | $0.60 |
| **Fallback (80% free)** | $0.022 | $0.22 | $2.20 |
| **Paid only (Flash Lite)** | $0.11 | $1.10 | $11.00 |
| **Paid only (Flash)** | $0.28 | $2.75 | $27.50 |

---

## Benefits

### 1. Cost Optimization

- **95%+ free processing** under normal conditions
- Pay only when free tier unavailable
- Expected cost: <$0.10/month for most use cases

### 2. Reliability

- **Automatic recovery** from API failures
- No manual intervention required
- Production-ready reliability

### 3. Performance

- **Free tier first** minimizes latency when available
- **Paid tier backup** maintains speed when needed
- No performance degradation during fallback

### 4. Transparency

- **Detailed logging** of all fallback events
- **Metadata tracking** shows which model was used
- Easy to monitor and audit costs

---

## Testing

### Manual Testing

```bash
# Test with your wind document
uv run python -m data_ingestor.cli process \
  --input data/wind_docs/Where-does-wind-matter.pdf \
  --output test_output/fallback_test.json

# Check the logs for fallback behavior
# Check metadata in output:
cat test_output/fallback_test.json | jq '.metadata | {llm_model, llm_fallback_used}'
```

### Test Fallback Configuration

```bash
# View current configuration
uv run python -c "
import os
from src.data_ingestor.parsers.pdf_parser import MarkerParser

parser = MarkerParser()
print(f'Primary: {parser.llm_model_primary}')
print(f'Fallback: {parser.llm_model_fallback}')
print(f'Enabled: {parser.enable_fallback}')
"
```

---

## Troubleshooting

### Fallback Not Working

**Check configuration:**
```bash
grep MARKER_ .env
```

**Expected output:**
```
MARKER_USE_LLM=true
MARKER_LLM_MODEL=meta-llama/llama-4-maverick:free
MARKER_LLM_FALLBACK_MODEL=google/gemini-2.5-flash-lite
MARKER_ENABLE_FALLBACK=true
```

### Both Models Failing

**Check API key:**
```bash
echo $OPENROUTER_API_KEY
```

**Test API connectivity:**
```bash
curl -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  https://openrouter.ai/api/v1/models | jq '.data[0]'
```

### Unexpected Costs

**Monitor usage:**
1. Check logs for fallback frequency
2. Review metadata to see fallback_used ratio
3. Adjust primary model if needed

**Disable fallback temporarily:**
```bash
# .env
MARKER_ENABLE_FALLBACK=false
```

---

## Advanced Configuration

### Custom Fallback Chain

You can implement multi-tier fallback by modifying the parser:

```python
# Example: Free → Cheap Paid → Premium Paid
# Would require code modification in pdf_parser.py
```

### Conditional Fallback

```python
# Example: Only fallback for critical documents
# Would require code modification in pdf_parser.py
```

### Cost Limits

```bash
# Future enhancement (not yet implemented)
MARKER_MAX_FALLBACK_COST_PER_DAY=1.00
```

---

## Implementation Details

### Code Location

- **Parser:** [src/data_ingestor/parsers/pdf_parser.py:374-718](../src/data_ingestor/parsers/pdf_parser.py#L374-L718)
- **Configuration:** [.env](../.env)
- **Example:** [.env.example](../.env.example)

### Key Methods

- `__init__()` - Loads primary and fallback configuration
- `_process_with_llm()` - Processes with specific LLM model
- `_process_without_llm()` - Processes without LLM enhancement
- `parse()` - Main method with fallback logic

### Error Detection

The fallback is triggered by checking error messages for keywords:
```python
is_api_error = any(keyword in error_str for keyword in [
    "api", "connection", "timeout", "rate limit", "unavailable",
    "endpoint", "403", "429", "500", "502", "503", "504"
])
```

---

## Monitoring

### Key Metrics to Track

1. **Fallback Rate:** What % of documents trigger fallback?
2. **Cost per Month:** Actual costs from paid tier usage
3. **Error Rate:** How often do both models fail?
4. **Processing Time:** Impact on performance

### Logging Analysis

```bash
# Count fallback events in logs
grep "Attempting fallback to" logs/*.log | wc -l

# Find failed primary attempts
grep "Primary model.*failed" logs/*.log

# Check final model usage
grep "Model used:" test_output/*.json | sort | uniq -c
```

---

## FAQ

### Q: What happens if both models fail?

**A:** The parser falls back to processing without LLM enhancement (basic Marker). You'll still get text extraction, just without LLM-enhanced table/math extraction.

### Q: Can I use two free models?

**A:** Yes, configure both as free models. However, if both have the same availability issues, you won't gain reliability benefits.

### Q: Can I use two paid models?

**A:** Yes, for example: primary = Flash Lite (cheap), fallback = Flash (premium). This gives cost optimization while maintaining quality fallback.

### Q: How do I disable fallback completely?

**A:** Set `MARKER_ENABLE_FALLBACK=false` in your .env file.

### Q: Will this slow down processing?

**A:** Only when fallback is triggered (rare). Normal processing uses the primary model directly with no overhead.

### Q: How do I know if fallback was used?

**A:** Check the metadata: `result.metadata['llm_fallback_used']` will be `true` if fallback was triggered.

---

## Next Steps

1. ✅ **Configuration set** - Your .env is already configured
2. ✅ **Ready to use** - Process your documents normally
3. 📊 **Monitor usage** - Track fallback rate and costs
4. 🔧 **Adjust if needed** - Fine-tune models based on your needs

---

**Last Updated:** 2025-11-03
**Related Documentation:**
- [Model Comparison](MODEL_COMPARISON_FOR_MARKER.md)
- [Vision Model Analysis](MARKER_VISION_MODEL_ANALYSIS.md)
- [Marker LLM POC](MARKER_LLM_POC_README.md)
