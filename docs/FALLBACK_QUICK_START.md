# LLM Fallback - Quick Start

**Status:** ✅ **Configured and Ready**

---

## TL;DR

Your Marker parser now automatically:
1. ✅ Tries **Llama 4 Maverick (FREE)** first
2. ✅ Falls back to **Gemini 2.5 Flash Lite (PAID)** if the free model fails
3. ✅ Only pays when necessary (~$0.06/month for typical usage)

**No code changes needed - it just works!**

---

## Your Current Configuration

[.env](../.env) is already configured:

```bash
MARKER_USE_LLM=true
MARKER_LLM_MODEL=meta-llama/llama-4-maverick:free                # Primary (FREE)
MARKER_LLM_FALLBACK_MODEL=google/gemini-2.5-flash-lite           # Fallback (PAID)
MARKER_ENABLE_FALLBACK=true                                       # Enabled
```

---

## How It Works

```
┌─────────────┐
│ Process PDF │
└──────┬──────┘
       │
       ▼
Try Llama 4 Maverick (FREE)
       │
       ├─ ✓ Success ──────────┐
       │                       │
       ├─ ✗ API Error         │
       │    (timeout, rate     │
       │     limit, etc.)      │
       │                       │
       ▼                       │
Try Gemini Flash Lite (PAID)  │
       │                       │
       ├─ ✓ Success ──────────┤
       │                       │
       ├─ ✗ Error             │
       │                       │
       ▼                       │
Process without LLM            │
       │                       │
       └───────────────────────┘
       │
       ▼
    DONE
```

---

## Usage (No Changes Required!)

```bash
# Use CLI as normal
uv run python -m data_ingestor.cli process \
  --input data/wind_docs/Where-does-wind-matter.pdf \
  --output test_output/result.json

# Check logs to see which model was used
# Check metadata: result.metadata['llm_model']
```

---

## Expected Costs

| Scenario | Monthly Cost (10K pages) |
|----------|--------------------------|
| Free model works 100% | $0.00 |
| Free model works 95% (realistic) | ~$0.06 |
| Free model works 80% (conservative) | ~$0.22 |
| Free model completely down | ~$1.10 |

**Most likely:** Less than **$0.10/month**

---

## What Changed

### Before (No Fallback)
```bash
MARKER_LLM_MODEL=google/gemini-2.5-flash
# Cost: ~$2.75/month for 10K pages
# Reliability: Depends on one model
```

### After (With Fallback)
```bash
MARKER_LLM_MODEL=meta-llama/llama-4-maverick:free
MARKER_LLM_FALLBACK_MODEL=google/gemini-2.5-flash-lite
MARKER_ENABLE_FALLBACK=true

# Cost: ~$0.06/month for 10K pages (95% free)
# Reliability: Automatic failover to paid tier
```

**Savings:** ~$2.69/month (97% cost reduction!)

---

## Monitoring

### Check which model was used:

```bash
# View metadata
cat test_output/result.json | jq '.metadata | {llm_model, llm_fallback_used}'
```

**Example output:**

```json
{
  "llm_model": "meta-llama/llama-4-maverick:free",
  "llm_fallback_used": false
}
```

### Check logs:

```
INFO - ✓ Successfully processed with primary model: meta-llama/llama-4-maverick:free
```

**Or if fallback triggered:**

```
WARNING - Primary model (meta-llama/llama-4-maverick:free) failed with API error: timeout
INFO - Attempting fallback to: google/gemini-2.5-flash-lite
INFO - ✓ Successfully processed with fallback model: google/gemini-2.5-flash-lite
```

---

## Options

### Disable Fallback (Free Only)

```bash
# .env
MARKER_ENABLE_FALLBACK=false
```

**Use when:** Absolute cost control, accept failures

### Change Fallback Model

**More expensive, better quality:**
```bash
MARKER_LLM_FALLBACK_MODEL=google/gemini-2.5-flash
# Cost: $0.075/1M vs $0.03/1M (2.5x more expensive)
```

**Different free model:**
```bash
MARKER_LLM_MODEL=meta-llama/llama-4-scout:free
# Slightly slower, still good quality
```

---

## Troubleshooting

### "Both models failed"

1. Check API key: `echo $OPENROUTER_API_KEY`
2. Check connectivity: `curl https://openrouter.ai/api/v1/models`
3. Review logs for specific errors

### "Unexpected costs"

1. Check fallback usage: `grep "fallback" logs/*.log | wc -l`
2. Review metadata: `jq '.metadata.llm_fallback_used' test_output/*.json`
3. Consider disabling fallback if costs too high

### "Primary model always failing"

- Free model may be down or rate-limited
- Check OpenRouter dashboard for model status
- Consider switching to different free model

---

## Next Steps

1. ✅ **You're all set!** - Just use Marker normally
2. 📊 **Monitor usage** - Check logs/metadata after processing
3. 💰 **Review costs** - Check OpenRouter dashboard monthly
4. 🔧 **Adjust if needed** - Change models based on your experience

---

## Documentation

**Full Documentation:**
- [LLM Fallback Mechanism](LLM_FALLBACK_MECHANISM.md) - Complete guide
- [Model Comparison](MODEL_COMPARISON_FOR_MARKER.md) - Model quality differences
- [Vision Model Analysis](MARKER_VISION_MODEL_ANALYSIS.md) - Detailed analysis

**Configuration:**
- [.env](../.env) - Your current configuration
- [.env.example](../.env.example) - Template with all options

---

**Last Updated:** 2025-11-03
**Status:** Production Ready
