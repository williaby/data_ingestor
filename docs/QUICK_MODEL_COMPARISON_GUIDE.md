# Quick Model Comparison Guide

**Goal:** See actual differences between vision models on YOUR wind documents

---

## TL;DR - Run This Command

```bash
cd /home/byron/dev/data_ingestor

# Test all three models on your wind document
uv run python scripts/compare_vision_models.py

# Or test on a different PDF
uv run python scripts/compare_vision_models.py path/to/your/document.pdf
```

This will automatically:
1. ✅ Test all 3 models (Llama free, Gemini Lite, Gemini Flash)
2. ✅ Extract text/tables/images from your wind document
3. ✅ Save side-by-side comparison outputs
4. ✅ Generate a detailed comparison report

**Processing time:** ~5-10 minutes for all three models

---

## What You'll Get

After running the comparison, you'll find in `test_output/model_comparison/`:

### 1. Comparison Report (`comparison_report.md`)
Summary table showing:
- Processing time for each model
- Number of elements extracted
- Number of tables found
- Cost per model
- Recommendations

### 2. Model Outputs (3 sets of files)

**For each model:**
- `{model}_output.md` - Full extracted text in markdown format
- `{model}_output.json` - Structured data with all elements

**Example files:**
```
llama-4-maverick-free_output.md
llama-4-maverick-free_output.json
gemini-2.5-flash-lite_output.md
gemini-2.5-flash-lite_output.json
gemini-2.5-flash_output.md
gemini-2.5-flash_output.json
```

### 3. What to Compare

**Open the markdown files side-by-side and check:**

#### ✅ Table Quality
Look for your data tables. Compare:
- Are all columns present?
- Are values aligned correctly?
- Are units preserved (m/s, GWh, etc.)?
- Are special characters preserved (±, °, ³)?

#### ✅ Technical Terminology
Search for domain-specific terms:
- LCOE (Levelized Cost of Energy)
- Capacity Factor
- Weibull distribution
- IEC standards
Are they spelled correctly? Context preserved?

#### ✅ Multi-Column Layout
Does the text flow naturally left-to-right?
Or do you see column mixing like:
```
"The wind speed measured at   In the coastal region,
Site A was 7.2 m/s while     turbines operate at..."
```

#### ✅ Equations & Math
Check for mathematical formulas:
- Are superscripts preserved (v³ not v3)?
- Are Greek letters correct (ρ not p)?
- Are equations readable?

---

## Expected Differences (Quick Reference)

### Tables

**Llama 4 Maverick (Free):**
```markdown
| Site | Speed | Energy |
|------|-------|--------|
| A    | 7.2   | 145    |
```
→ Basic structure, may lose some details

**Gemini Flash Lite:**
```markdown
| Site | Wind Speed (m/s) | Annual Energy (GWh) |
|------|------------------|---------------------|
| A    | 7.2 ± 0.3        | 145.2               |
```
→ Better structure, preserves units and symbols

**Gemini Flash:**
```markdown
| Site | Mean Wind Speed (m/s) | Annual Energy (GWh) | Capacity Factor (%) |
|------|-----------------------|---------------------|---------------------|
| A    | 7.2 ± 0.3             | 145.2               | 32.1                |
```
→ Best structure, may capture additional columns

### Technical Terms

**Llama:** Good recognition, occasional errors on rare acronyms

**Gemini Lite:** Excellent recognition, understands context

**Gemini Flash:** Best recognition, can infer relationships

### Speed

- **Llama:** ~3-4s per page
- **Gemini Lite:** ~0.8-1s per page (fastest)
- **Gemini Flash:** ~1-1.5s per page

---

## Decision Framework

After reviewing your comparison results:

### Choose Llama 4 Maverick (FREE) If:

- ✅ Tables look acceptable (minor issues OK)
- ✅ Technical terms are mostly correct
- ✅ You're still in development/testing
- ✅ Cost is critical constraint
- ✅ Low volume (<100 docs/month)

**Cost:** $0/month forever

### Choose Gemini 2.5 Flash Lite If: ⭐

- ✅ Tables are noticeably better structured
- ✅ Technical accuracy improved
- ✅ Faster processing is valuable
- ✅ Production RAG system
- ✅ Moderate to high volume

**Cost:** ~$1-2/month for typical usage
**This is the recommended option for most production use cases**

### Choose Gemini 2.5 Flash If:

- ✅ Quality difference is significant on YOUR documents
- ✅ Flash Lite struggles with complex tables/figures
- ✅ Mission-critical documents
- ✅ Budget allows for premium

**Cost:** ~$3-5/month for typical usage
**Use for critical documents only**

---

## Next Steps After Comparison

### 1. Review the Outputs
```bash
cd test_output/model_comparison

# Open comparison report
cat comparison_report.md

# Compare markdown outputs side-by-side
diff llama-4-maverick-free_output.md gemini-2.5-flash-lite_output.md
```

### 2. Test with More Documents

```bash
# Test with your most challenging PDFs
uv run python scripts/compare_vision_models.py data/wind_docs/complex_table_doc.pdf
uv run python scripts/compare_vision_models.py data/wind_docs/scanned_document.pdf
```

### 3. Configure Your Choice

Edit [.env](../.env):

```bash
# For free model
MARKER_USE_LLM=true
MARKER_LLM_MODEL=meta-llama/llama-4-maverick:free

# For paid model (recommended)
MARKER_USE_LLM=true
MARKER_LLM_MODEL=google/gemini-2.5-flash-lite

# For premium quality
MARKER_USE_LLM=true
MARKER_LLM_MODEL=google/gemini-2.5-flash
```

### 4. Process Your Full Document Set

```bash
# Process all wind documents with chosen model
for pdf in data/wind_docs/*.pdf; do
  uv run python -m data_ingestor.cli process \
    --input "$pdf" \
    --output "test_output/processed/$(basename $pdf .pdf).json"
done
```

---

## Troubleshooting

### "No vision models working"
- Check your `.env` file has `OPENROUTER_API_KEY` set
- Verify the key is correct: `echo $OPENROUTER_API_KEY`
- Check privacy settings on OpenRouter dashboard

### "Model X returned empty output"
- Some models don't support vision (Gemma has issues)
- Try a different model from the recommended list
- Check error messages in the output

### "Comparison taking too long"
- Each model processes the full PDF (can take 5-10 min total)
- You can Ctrl+C to stop and review partial results
- Consider testing on a shorter PDF first

---

## Quick Reference: Model Specs

| Model | Cost | Speed | Quality | Best For |
|-------|------|-------|---------|----------|
| Llama 4 Maverick (Free) | $0 | Medium | Good | Development, testing |
| Gemini 2.5 Flash Lite | $0.03/1M | Fast | Excellent | Production (recommended) |
| Gemini 2.5 Flash | $0.075/1M | Medium | Best | Critical documents |

---

**Last Updated:** 2025-11-03
**Related Docs:**
- [Full Model Comparison](MODEL_COMPARISON_FOR_MARKER.md)
- [Vision Model Analysis](MARKER_VISION_MODEL_ANALYSIS.md)
- [Test Script](../scripts/compare_vision_models.py)
