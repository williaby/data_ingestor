#!/usr/bin/env python3
"""Analyze benchmark results from phase1-baseline.json"""

import json
from collections import Counter
from pathlib import Path

results_file = Path("results/phase1-baseline.json")

with open(results_file) as f:
    data = json.load(f)


# Overall stats
overall = data.get("overall", {})

# Dataset results
datasets = data.get("datasets", {})

for _ds_name, ds_data in datasets.items():

    for _parser_name, parser_data in ds_data.items():

        # Get results
        results = parser_data.get("results", [])
        successful = [r for r in results if r.get("success", False)]
        failed = [r for r in results if not r.get("success", False)]

        # Analyze failures
        if failed:
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

            for _error_type, _count in error_types.most_common(10):
                pass

        # Analyze metrics
        if successful:

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
