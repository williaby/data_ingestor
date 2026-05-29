#!/usr/bin/env python3
"""Analyze benchmark results from phase1-baseline.json"""

import json
from collections import Counter
from pathlib import Path

results_file = Path("results/phase1-baseline.json")

with open(results_file) as f:
    data = json.load(f)

print("=" * 80)
print("PHASE 1 BASELINE BENCHMARK RESULTS ANALYSIS")
print("=" * 80)

# Overall stats
print("\n📊 OVERALL STATISTICS")
print("-" * 80)
overall = data.get("overall", {})
print(f"Total documents:    {overall.get('total_documents', 0)}")
print(f"Successful:         {overall.get('total_successful', 0)} ({overall.get('success_rate', 0)*100:.1f}%)")
print(f"Failed:             {overall.get('total_failed', 0)} ({overall.get('failure_rate', 0)*100:.1f}%)")
print(f"Total time:         {overall.get('total_time', 0):.2f}s ({overall.get('total_time', 0)/60:.1f} minutes)")
print(f"Throughput:         {overall.get('throughput_docs_per_hour', 0):.2f} docs/hour")
print(f"Start time:         {overall.get('start_time', 'N/A')}")
print(f"End time:           {overall.get('end_time', 'N/A')}")

# Dataset results
print("\n📁 DATASET RESULTS")
print("-" * 80)
datasets = data.get("datasets", {})

for ds_name, ds_data in datasets.items():
    print(f"\n{ds_name.upper()}")

    for parser_name, parser_data in ds_data.items():
        print(f"\n  Parser: {parser_name}")

        # Get results
        results = parser_data.get("results", [])
        successful = [r for r in results if r.get("success", False)]
        failed = [r for r in results if not r.get("success", False)]

        print(f"    Total results:    {len(results)}")
        print(f"    Successful:       {len(successful)} ({len(successful)/len(results)*100:.1f}%)")
        print(f"    Failed:           {len(failed)} ({len(failed)/len(results)*100:.1f}%)")

        # Analyze failures
        if failed:
            print("\n    Failure Analysis:")
            error_types = Counter()
            for result in failed:
                error = result.get("error", "Unknown error")
                # Categorize errors
                if "Ground truth" in error or "not found" in error:
                    error_types["Missing ground truth"] += 1
                elif "layout" in error.lower():
                    error_types["Layout detection error"] += 1
                elif "parsing" in error.lower() or "parse" in error.lower():
                    error_types["Parsing error"] += 1
                elif "evaluation" in error.lower():
                    error_types["Evaluation error"] += 1
                else:
                    error_types[error[:60]] += 1

            for error_type, count in error_types.most_common(10):
                print(f"      - {error_type}: {count}")

        # Analyze metrics
        if successful:
            print("\n    Metrics (successful documents):")

            # Collect all metrics
            all_metrics = {}
            for result in successful:
                for metric in result.get("metrics", []):
                    metric_name = metric.get("name")
                    metric_value = metric.get("value")
                    if metric_name and metric_value is not None:
                        if metric_name not in all_metrics:
                            all_metrics[metric_name] = []
                        all_metrics[metric_name].append(metric_value)

            # Print statistics for each metric
            for metric_name, values in sorted(all_metrics.items()):
                if values:
                    mean_val = sum(values) / len(values)
                    min_val = min(values)
                    max_val = max(values)
                    print(f"      {metric_name}:")
                    print(f"        Mean: {mean_val:.4f}")
                    print(f"        Range: [{min_val:.4f}, {max_val:.4f}]")
                    print(f"        Count: {len(values)} documents")

print("\n" + "=" * 80)
