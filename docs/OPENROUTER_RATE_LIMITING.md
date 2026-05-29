# OpenRouter Rate Limiting Implementation

## Overview

This document describes the rate limiting implementation for OpenRouter API calls in the Data Ingestor project, specifically for Marker's LLM-enhanced PDF processing.

## OpenRouter Rate Limits (2025)

OpenRouter enforces the following rate limits:

### Free Tier (< $10 in credits)
- **20 requests per minute (RPM)** for `:free` models
- **50 requests per day** total for `:free` models
- No platform limits for paid models

### Paid Tier ($10+ in credits purchased)
- **20 requests per minute (RPM)** for `:free` models
- **1,000 requests per day** for `:free` models
- No platform limits for paid models
- **Note**: Once you've purchased $10 in credits, you keep these higher limits even if your balance drops below $10

### Paid Models (non-`:free`)
- **No platform-level rate limits**
- Individual model providers (OpenAI, Anthropic, Google, etc.) may have their own limits

## Implementation Architecture

### Core Components

#### 1. `RateLimiter` Class ([src/data_ingestor/utils/rate_limiter.py](src/data_ingestor/utils/rate_limiter.py))

Thread-safe rate limiter implementing:
- **Token bucket algorithm** for per-minute limits (RPM)
- **Sliding window** for daily request tracking
- **Configurable limits** based on tier (free/paid)
- **Statistics tracking** for monitoring

```python
limiter = RateLimiter(
    rpm_limit=20,
    daily_limit=1000,
    tier="paid"
)

# Acquire permission (blocks until available)
if limiter.acquire(timeout=300.0):
    # Make API call
    pass
```

#### 2. `OpenRouterRateLimiter` Class

Manages separate rate limiters for free and paid models:
- Routes requests to appropriate limiter based on model name
- Free models (ending in `:free`) use strict 20 RPM limit
- Paid models use generous limits (effectively no platform limit)

```python
limiter = OpenRouterRateLimiter(tier="paid")

# Automatically routes to correct limiter
limiter.acquire("meta-llama/llama-4-maverick:free")  # Uses free limiter (20 RPM)
limiter.acquire("google/gemini-2.5-flash-lite")      # Uses paid limiter (no limit)
```

#### 3. MarkerParser Integration ([src/data_ingestor/parsers/pdf_parser.py](src/data_ingestor/parsers/pdf_parser.py))

Rate limiter is integrated into MarkerParser's `_process_with_llm()` method:
- Acquires rate limit permission before each API call
- Implements exponential backoff on 429 (rate limit) errors
- Logs detailed statistics for monitoring

## Configuration

### Environment Variables (.env)

```bash
# OpenRouter Tier: "free" (< $10 credits) or "paid" ($10+ credits)
DATA_INGESTOR_OPENROUTER_TIER=paid

# Enable rate limiting (recommended)
DATA_INGESTOR_OPENROUTER_ENABLE_RATE_LIMITING=true

# Maximum wait time for rate limit slot (seconds)
DATA_INGESTOR_OPENROUTER_RATE_LIMIT_TIMEOUT=300.0
```

### Settings (src/data_ingestor/core/config.py)

```python
class Settings(BaseSettings):
    # OpenRouter API rate limiting
    openrouter_tier: str = "paid"
    openrouter_rpm_limit: int = 20
    openrouter_daily_limit_free: int = 50
    openrouter_daily_limit_paid: int = 1000
    openrouter_enable_rate_limiting: bool = True
    openrouter_rate_limit_timeout: float = 300.0
```

## Error Handling

### Error Classification

The implementation classifies API errors into categories for appropriate handling:

#### 1. Rate Limit Errors (429)
- **Cause**: Exceeded 20 RPM or daily limit
- **Handling**: Exponential backoff (1s, 2s, 4s) with up to 3 retries
- **Fallback**: Switches to paid model if primary (free) model fails

#### 2. Authentication Errors (401/403)
- **Cause**: Invalid or missing `OPENROUTER_API_KEY`
- **Handling**: Fails immediately with clear error message
- **Fallback**: No automatic fallback (user must fix API key)

#### 3. Downstream Provider Errors (400)
- **Cause**: Limits from downstream providers (OpenAI, etc.)
- **Handling**: Logged as warning, attempts fallback to paid model
- **Note**: These are NOT OpenRouter limits, but provider limits passed through

#### 4. Server Errors (500-504)
- **Cause**: Temporary OpenRouter or provider issues
- **Handling**: Attempts fallback to paid model
- **Fallback**: May succeed if issue is model-specific

#### 5. Connection Errors
- **Cause**: Network issues, timeouts
- **Handling**: Attempts fallback to paid model
- **Fallback**: May succeed if primary was unreachable

### Exponential Backoff

On 429 rate limit errors, the system retries with exponential backoff:

```
Attempt 1: Immediate
Attempt 2: Wait 1 second, retry
Attempt 3: Wait 2 seconds, retry
Attempt 4: Wait 4 seconds, retry
Final: Fail if all retries exhausted
```

## Model Fallback Strategy

### Primary Model (Free Tier)
- Default: `meta-llama/llama-4-maverick:free`
- Subject to 20 RPM and 1,000/day limits (paid tier)
- Best free vision model available

### Fallback Model (Paid Tier)
- Default: `google/gemini-2.5-flash-lite`
- No platform limits
- Cost: ~$0.03/1M tokens
- Triggered automatically on primary model errors

### Fallback Logic

```
1. Try primary model (free tier)
   ↓ (on API error)
2. Classify error type
   ↓ (if API-related and fallback enabled)
3. Try fallback model (paid tier)
   ↓ (on failure)
4. Try without LLM enhancement
   ↓ (last resort)
5. Fail gracefully
```

## Monitoring and Statistics

### Rate Limiter Statistics

```python
stats = limiter.get_stats()
# Returns:
{
    "total_requests": 42,
    "total_waits": 5,
    "total_wait_time": 12.5,
    "avg_wait_time": 2.5,
    "current_rpm": 15,
    "rpm_limit": 20,
    "rpm_utilization": 0.75,
    "current_daily": 42,
    "daily_limit": 1000,
    "daily_utilization": 0.042
}
```

### Log Output

The implementation logs detailed information:

```
INFO - OpenRouter rate limiting enabled (paid tier)
INFO - Acquiring rate limit permission for meta-llama/llama-4-maverick:free...
INFO - ✓ Rate limit permission acquired
DEBUG - Rate limiter stats: {'current_rpm': 5, 'rpm_utilization': 0.25, ...}
WARNING - Rate limit error detected (429): Too many requests
INFO - Attempting fallback to: google/gemini-2.5-flash-lite
INFO - ✓ Successfully processed with fallback model
```

## Usage Examples

### Basic Usage (Automatic)

Rate limiting is enabled by default and works transparently:

```bash
# Process PDF with LLM enhancement (rate limiting automatic)
uv run data-ingestor process document.pdf --output output.json
```

### Disable Rate Limiting (Not Recommended)

```bash
# In .env
DATA_INGESTOR_OPENROUTER_ENABLE_RATE_LIMITING=false
```

**Warning**: Disabling rate limiting may result in 429 errors and API blocks.

### Custom Timeout

```bash
# In .env
DATA_INGESTOR_OPENROUTER_RATE_LIMIT_TIMEOUT=600.0  # 10 minutes
```

### Tier Configuration

```bash
# Free tier (< $10 credits): 50 requests/day
DATA_INGESTOR_OPENROUTER_TIER=free

# Paid tier ($10+ credits): 1,000 requests/day
DATA_INGESTOR_OPENROUTER_TIER=paid
```

## Troubleshooting

### Problem: "Daily limit exceeded" error

**Solution 1: Upgrade to paid tier**
- Purchase at least $10 in OpenRouter credits
- Set `DATA_INGESTOR_OPENROUTER_TIER=paid`
- Increases daily limit from 50 to 1,000 requests

**Solution 2: Wait for limit reset**
- Daily limits reset 24 hours after oldest request
- Check logs for estimated reset time

### Problem: "Rate limit timeout exceeded" error

**Cause**: Too many concurrent requests or sustained high load

**Solution 1: Increase timeout**
```bash
DATA_INGESTOR_OPENROUTER_RATE_LIMIT_TIMEOUT=600.0  # 10 minutes
```

**Solution 2: Reduce concurrent processing**
- Process fewer PDFs simultaneously
- Use sequential processing instead of parallel

### Problem: 400/403 errors from downstream providers

**Cause**: OpenAI or other provider limits (NOT OpenRouter limits)

**Solution 1: Use paid models**
- Switch to paid models which have higher provider limits
- Set fallback model to paid tier model

**Solution 2: Contact provider**
- May need to upgrade OpenAI/provider account
- Check provider-specific rate limits

### Problem: Requests timing out

**Solution 1: Check network connectivity**
```bash
curl https://openrouter.ai/api/v1/models
```

**Solution 2: Verify API key**
```bash
# In .env
OPENROUTER_API_KEY=sk-or-v1-...
```

## Performance Impact

### With Rate Limiting (Recommended)

**Pros:**
- Prevents 429 errors and API blocks
- Ensures reliability for high-volume processing
- Provides predictable throughput

**Cons:**
- May add wait time when hitting RPM limit
- 20 RPM = max 3 seconds per request under load

### Without Rate Limiting (Not Recommended)

**Pros:**
- No artificial delays
- Faster for low-volume usage

**Cons:**
- Risk of 429 errors and processing failures
- May trigger API blocks or account suspension
- Unpredictable failures under load

## Best Practices

1. **Always enable rate limiting** for production use
2. **Use paid tier** ($10+ credits) for serious workloads (1,000/day vs 50/day)
3. **Monitor statistics** to track utilization and plan capacity
4. **Use paid models** for critical documents (no platform limits)
5. **Enable fallback** to paid models for reliability
6. **Set appropriate timeouts** based on your use case (default: 5 minutes)
7. **Log errors** and monitor for patterns (downstream vs OpenRouter)

## API Limits Comparison

| Tier | Model Type | RPM Limit | Daily Limit | Notes |
|------|------------|-----------|-------------|-------|
| Free | `:free` models | 20 | 50 | Very restrictive |
| Paid | `:free` models | 20 | 1,000 | 20x daily capacity |
| Any | Paid models | None | None | Provider limits may apply |

## Future Enhancements

### Planned Features
- [ ] Per-document cost tracking
- [ ] Daily cost limits with automatic cutoff
- [ ] Complexity-based routing (simple docs → free, complex → paid)
- [ ] Rate limit caching across process restarts
- [ ] Multi-process rate limit coordination
- [ ] Grafana/Prometheus metrics export

### Configuration Hooks (Not Yet Implemented)
```bash
# Future configuration
MARKER_ENABLE_COMPLEXITY_ROUTING=true
MARKER_UPGRADE_ON_COMPLEXITY=true
MARKER_MAX_COST_PER_DOCUMENT=0.10
MARKER_DAILY_COST_LIMIT=10.00
```

## Related Documentation

- [OpenRouter API Documentation](https://openrouter.ai/docs)
- [OpenRouter Rate Limits FAQ](https://openrouter.ai/docs/faq#getting-started)
- [Marker LLM Integration](MARKER_LLM_INTEGRATION.md)
- [Model Comparison Guide](MODEL_COMPARISON_FOR_MARKER.md)

## Testing

Comprehensive unit tests available in [tests/unit/test_rate_limiter.py](tests/unit/test_rate_limiter.py):

```bash
# Run rate limiter tests
uv run pytest tests/unit/test_rate_limiter.py -v

# Test specific scenarios
uv run pytest tests/unit/test_rate_limiter.py::TestRateLimiter::test_basic_rate_limiting -v
```

## Support

For issues with rate limiting:
1. Check logs for detailed error classification
2. Verify `.env` configuration matches your OpenRouter tier
3. Monitor statistics to identify bottlenecks
4. Review [troubleshooting section](#troubleshooting) above

---

**Last Updated**: 2025-11-05
**OpenRouter API Version**: v1
**Rate Limits Last Verified**: 2025-11-05
