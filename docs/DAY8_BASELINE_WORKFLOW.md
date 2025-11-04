# Day 8: Baseline Execution Workflow

**Phase**: 1.5 - Performance Benchmarking & Baseline Establishment
**Date**: 2025-11-04
**Status**: Ready for Execution

---

## Overview

Day 8 establishes Phase 1 baseline metrics by executing comprehensive benchmarks across all datasets with both parsers (PyMuPDF, PyMuPDF4LLM). This baseline will be used for Phase 2 comparison.

### Objectives

1. Validate all datasets are ready
2. Execute baseline benchmarks for both parsers
3. Collect comprehensive performance and quality metrics
4. Identify and categorize failure cases
5. Generate reports and documentation

---

## Prerequisites

### Dataset Requirements

All three datasets must be downloaded and validated:

- **READoc**: 500 samples (PDF + Markdown)
  - HuggingFace: `lazyc/READoc`
  - Location: `data/benchmarks/readoc/`

- **DocLayNet**: 1,000 samples (Images + JSON)
  - HuggingFace: `ds4sd/DocLayNet` (Parquet files)
  - Location: `data/benchmarks/doclaynet/`

- **PubTables**: 500 samples (Table images + JSON)
  - Source: Microsoft Table Transformer
  - Location: `data/benchmarks/pubtables/`

### System Requirements

- **Disk Space**: > 10 GB free
- **Memory**: 8 GB+ recommended
- **Time**: 2-4 hours for full baseline

---

## Workflow Steps

### Step 1: Pre-Flight Checks

**Purpose**: Validate environment before execution

```bash
# Run comprehensive pre-flight checks
python scripts/pre_flight_check.py

# Check specific dataset
python scripts/pre_flight_check.py --dataset readoc

# Export results for documentation
python scripts/pre_flight_check.py --export results/pre_flight_report.json
```

**Expected Output**:
- ✅ All datasets marked as "ready"
- ✅ Both parsers (PyMuPDF, PyMuPDF4LLM) available
- ✅ Sufficient disk space
- ✅ Output directories created

**If Checks Fail**:
- Review error messages
- Download missing datasets
- Install missing parser dependencies
- Free up disk space if needed

---

### Step 2: Test Run (Optional but Recommended)

**Purpose**: Validate pipeline works end-to-end

```bash
# Quick test with first available dataset and parser
python scripts/run_baseline.py --test

# Test specific dataset
python scripts/run_baseline.py --test --datasets readoc
```

**Expected Duration**: 5-10 minutes
**Expected Output**:
- Results: `results/test_run.json`
- Report: `reports/test_run.html`

**Verify**:
- ✅ Benchmark completes without errors
- ✅ Results file generated
- ✅ HTML report created
- ✅ Success rate > 95%

---

### Step 3: Full Baseline Execution

**Purpose**: Run complete Phase 1 baseline

#### Option A: Automated (Recommended)

```bash
# Run full baseline with both parsers
python scripts/run_baseline.py --full

# Custom configuration
python scripts/run_baseline.py --full \
  --datasets readoc doclaynet pubtables \
  --parsers pymupdf pymupdf4llm \
  --workers 4
```

**This will execute**:
1. Pre-flight validation
2. PyMuPDF baseline (all datasets)
3. PyMuPDF4LLM baseline (all datasets)
4. Combined baseline (both parsers)
5. Report generation
6. Execution logging

#### Option B: Manual (Step-by-Step)

```bash
# 1. PyMuPDF baseline
data-ingestor benchmark \
  --parsers pymupdf \
  --workers 4 \
  --output results/phase1_baseline_pymupdf.json

# 2. PyMuPDF4LLM baseline
data-ingestor benchmark \
  --parsers pymupdf4llm \
  --workers 4 \
  --output results/phase1_baseline_pymupdf4llm.json

# 3. Combined baseline (both parsers)
data-ingestor benchmark \
  --parsers pymupdf pymupdf4llm \
  --workers 4 \
  --output results/phase1_baseline_combined.json
```

**Expected Duration**: 2-4 hours
**Expected Throughput**: 100-200 docs/hour

---

### Step 4: Generate Reports

**Purpose**: Create comprehensive visualizations and exports

```bash
# HTML report (interactive)
data-ingestor benchmark-report \
  results/phase1_baseline_combined.json \
  --format html

# All formats (HTML, JSON, CSV)
data-ingestor benchmark-report \
  results/phase1_baseline_combined.json \
  --format all

# Custom output location
data-ingestor benchmark-report \
  results/phase1_baseline_combined.json \
  --format html \
  --output reports/phase1_final.html
```

**Generated Files**:
- `reports/phase1_baseline_combined.html` - Interactive HTML report
- `reports/phase1_baseline_combined_report.json` - Machine-readable
- `reports/phase1_baseline_combined_metrics.csv` - Analysis-ready

---

### Step 5: Failure Analysis

**Purpose**: Identify and categorize failures

```bash
# Analyze failures from results
python scripts/analyze_failures.py \
  results/phase1_baseline_combined.json

# Export analysis
python scripts/analyze_failures.py \
  results/phase1_baseline_combined.json \
  --export results/failure_analysis.json \
  --markdown results/failure_recommendations.md

# Analyze multiple result files
python scripts/analyze_failures.py \
  results/phase1_baseline_*.json \
  --export results/combined_failure_analysis.json
```

**Outputs**:
- Failure categorization (parsing, timeout, resource, ground truth)
- Error pattern identification
- Dataset/parser breakdown
- Prioritized recommendations

---

### Step 6: Metrics Extraction

**Purpose**: Extract and compare performance metrics

```bash
# Extract metrics from single file
python scripts/extract_metrics.py \
  results/phase1_baseline_combined.json

# Export to JSON and CSV
python scripts/extract_metrics.py \
  results/phase1_baseline_combined.json \
  --export results/metrics_summary.json \
  --csv results/parser_comparison.csv

# Compare multiple runs
python scripts/extract_metrics.py \
  results/phase1_baseline_pymupdf.json \
  results/phase1_baseline_pymupdf4llm.json \
  --compare \
  --export results/parser_comparison.json
```

**Outputs**:
- Overall performance summary
- Per-dataset metrics
- Per-parser metrics
- Quality metric aggregations
- Comparison tables

---

### Step 7: Documentation

**Purpose**: Document baseline results for Phase 2 comparison

Create comprehensive summary document: `docs/PHASE1_BASELINE_RESULTS.md`

**Include**:
1. **Execution Summary**
   - Date and duration
   - Configuration (workers, datasets, parsers)
   - Success/failure rates

2. **Performance Metrics**
   - Throughput (docs/hour)
   - Average processing times
   - Per-dataset performance

3. **Quality Metrics**
   - READoc: Section F1, List F1, Table F1, CER
   - DocLayNet: mAP, Reading Order F1, Kendall tau
   - PubTables: TEDS, Cell Match, Header F1

4. **Parser Comparison**
   - PyMuPDF vs PyMuPDF4LLM
   - Strengths and weaknesses
   - Use case recommendations

5. **Failure Analysis**
   - Common error patterns
   - Dataset-specific issues
   - Recommendations for Phase 2

6. **Phase 2 Targets**
   - Performance improvement goals
   - Quality metric targets
   - Expected speedup (> 4x)

---

## Expected Results

### Overall Performance (Phase 1 Baseline)

| Metric | Target | Rationale |
|--------|--------|-----------|
| **Throughput** | 100-200 docs/hr | Sequential processing, no optimization |
| **Success Rate** | > 95% | High reliability expected |
| **Failure Rate** | < 5% | Minimal failures |
| **Avg Processing Time** | 18-36 sec/doc | Baseline without acceleration |

### Quality Targets by Dataset

#### READoc (PDF→Markdown Structure)

| Metric | Phase 1 Target | Phase 2 Target |
|--------|----------------|----------------|
| Section F1 | 0.75-0.80 | > 0.85 |
| List F1 | 0.70-0.75 | > 0.80 |
| Table F1 | 0.70-0.80 | > 0.95 |
| Text CER | 0.08-0.12 | < 0.05 |

#### DocLayNet (Layout Detection)

| Metric | Phase 1 Target | Phase 2 Target |
|--------|----------------|----------------|
| mAP | 0.70-0.75 | > 0.80 |
| Reading Order F1 | 0.80-0.85 | > 0.90 |
| Kendall tau | 0.75-0.85 | > 0.85 |

#### PubTables (Table Structure)

| Metric | Phase 1 Target | Phase 2 Target |
|--------|----------------|----------------|
| TEDS | 0.75-0.80 | > 0.95 |
| Cell Exact Match | 0.65-0.75 | > 0.85 |
| Header F1 | 0.75-0.85 | > 0.90 |

---

## Troubleshooting

### Issue: Pre-Flight Checks Fail

**Symptoms**: Datasets marked as "empty" or "partial"

**Solutions**:
1. Verify dataset downloads completed
2. Check directory structure:
   ```bash
   ls -la data/benchmarks/*/documents/
   ls -la data/benchmarks/*/ground_truth/
   ```
3. Re-run download scripts if needed
4. Validate file formats match expectations

### Issue: Benchmark Hangs or Times Out

**Symptoms**: Progress bars stop, no activity

**Solutions**:
1. Check for problematic documents (large PDFs, complex tables)
2. Increase timeout: modify `timeout_per_doc` in config
3. Reduce workers: `--workers 2`
4. Monitor system resources: `htop` or `top`

### Issue: High Failure Rate (> 10%)

**Symptoms**: Many documents failing to parse

**Solutions**:
1. Run failure analysis: `python scripts/analyze_failures.py results/*.json`
2. Check parser logs for error patterns
3. Validate ground truth files exist
4. Review dataset integrity

### Issue: Out of Memory

**Symptoms**: Process killed, memory errors

**Solutions**:
1. Reduce workers: `--workers 2`
2. Process datasets separately
3. Close other applications
4. Upgrade system memory if possible

### Issue: Reports Not Generated

**Symptoms**: HTML/CSV reports missing

**Solutions**:
1. Check results file exists
2. Verify `reports/` directory is writable
3. Re-run report generation manually
4. Check for JSON format errors in results

---

## Quality Checks

Before considering Day 8 complete, verify:

### ✅ Execution Checklist

- [ ] Pre-flight checks passed
- [ ] Test run completed successfully
- [ ] PyMuPDF baseline executed
- [ ] PyMuPDF4LLM baseline executed
- [ ] Combined baseline executed
- [ ] All reports generated
- [ ] Failure analysis completed
- [ ] Metrics extracted
- [ ] Documentation updated

### ✅ Results Validation

- [ ] All 2,000 documents processed (500 + 1,000 + 500)
- [ ] Success rate > 95%
- [ ] Failure rate < 5%
- [ ] Throughput within expected range (100-200 docs/hr)
- [ ] Quality metrics within target ranges
- [ ] No critical errors in logs

### ✅ Documentation

- [ ] Execution log saved: `results/execution_log.json`
- [ ] Pre-flight report: `results/pre_flight_report.json`
- [ ] Failure analysis: `results/failure_analysis.json`
- [ ] Metrics summary: `results/metrics_summary.json`
- [ ] Baseline results doc: `docs/PHASE1_BASELINE_RESULTS.md`

---

## File Organization

### Results Files

```
results/
├── pre_flight_report.json        # Pre-flight validation
├── test_run.json                 # Test run results
├── phase1_baseline_pymupdf.json  # PyMuPDF baseline
├── phase1_baseline_pymupdf4llm.json  # PyMuPDF4LLM baseline
├── phase1_baseline_combined.json # Combined baseline
├── failure_analysis.json         # Failure categorization
├── metrics_summary.json          # Extracted metrics
├── parser_comparison.csv         # Comparison table
└── execution_log.json            # Execution tracking
```

### Report Files

```
reports/
├── test_run.html                          # Test run report
├── phase1_baseline_pymupdf.html           # PyMuPDF report
├── phase1_baseline_pymupdf4llm.html       # PyMuPDF4LLM report
├── phase1_baseline_combined.html          # Combined report
├── phase1_baseline_combined_report.json   # JSON export
└── phase1_baseline_combined_metrics.csv   # CSV export
```

---

## Next Steps (Day 9)

After Day 8 completion:

1. **Deep Dive Analysis**
   - Compare PyMuPDF vs PyMuPDF4LLM performance
   - Identify parser strengths/weaknesses
   - Analyze dataset-specific patterns

2. **Visualization**
   - Create charts comparing parsers
   - Generate quality metric heatmaps
   - Build timeline visualizations

3. **Recommendations**
   - Document findings for Phase 2
   - Prioritize improvement areas
   - Define Phase 2 success criteria

4. **CI/CD Integration** (Day 10)
   - Create GitHub Actions workflow
   - Set up regression detection
   - Automate benchmark execution

---

## Reference

- **Full Plan**: [Day 8 Implementation Plan](../tmp_cleanup/.tmp-phase1.5-day8-plan-20251104.md)
- **Project Plan**: [PROJECT_PLAN.md](PROJECT_PLAN.md)
- **Benchmarking Guide**: [PERFORMANCE_BENCHMARKING_GUIDE.md](PERFORMANCE_BENCHMARKING_GUIDE.md)
- **Datasets**: [data/benchmarks/README.md](../data/benchmarks/README.md)

---

**Status**: Ready for Execution 🚀
**Prerequisites**: Datasets downloaded and validated
**Expected Duration**: 3-5 hours (including analysis and documentation)
**Owner**: Development Team
**Last Updated**: 2025-11-04
