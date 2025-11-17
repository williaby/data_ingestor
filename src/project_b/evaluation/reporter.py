"""
Report generation for validation results.

This module provides HTML and CSV report generation for layout detection
validation results. JSON export is handled directly by the validator.

**Functions:**
- generate_html_report: Create HTML report with tables and visualizations
- generate_csv_report: Create CSV report with metrics tables
- save_report: Save report to file (auto-detects format from extension)

Schema Version: 1.0.0
"""

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from project_b.layout.detector import DOCLAYNET_CLASS_MAPPING


def generate_html_report(results: dict[str, Any]) -> str:
    """
    Generate HTML report from validation results.

    Args:
        results: Validation results dictionary from validate_on_dataset()

    Returns:
        HTML string with formatted report

    **Report Sections:**
    - Overall metrics (mAP, processing time, num images)
    - Per-class Average Precision table
    - Per-class Precision/Recall/F1 table
    - Confusion matrix heatmap
    - Timing statistics

    **Example:**
        ```python
        from project_b.evaluation import validate_on_dataset, generate_html_report

        results = validate_on_dataset(detector, dataset_path, annotations_path)
        html = generate_html_report(results)

        with open("report.html", "w") as f:
            f.write(html)
        ```
    """
    # Extract metrics
    map_score = results["metrics"]["mAP"]
    per_class_ap = results["metrics"]["per_class_AP"]
    per_class_metrics = results["metrics"]["per_class_metrics"]
    confusion_matrix = np.array(results["metrics"]["confusion_matrix"])
    num_images = results["num_images_processed"]
    avg_time = results["timing"]["avg_inference_time_ms"]
    total_time = results["timing"]["total_time_seconds"]

    # Build HTML
    html_parts = []

    # Header
    html_parts.append("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Layout Detection Validation Report</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        h2 {
            color: #34495e;
            margin-top: 30px;
            border-bottom: 2px solid #95a5a6;
            padding-bottom: 5px;
        }
        .metric-card {
            background: white;
            padding: 20px;
            margin: 15px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #3498db;
        }
        .metric-label {
            font-size: 0.9em;
            color: #7f8c8d;
            text-transform: uppercase;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            margin: 15px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }
        th {
            background-color: #3498db;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }
        td {
            padding: 10px 12px;
            border-bottom: 1px solid #ecf0f1;
        }
        tr:last-child td {
            border-bottom: none;
        }
        tr:hover {
            background-color: #f8f9fa;
        }
        .confusion-matrix {
            overflow-x: auto;
        }
        .confusion-cell {
            text-align: center;
            min-width: 60px;
            font-size: 0.85em;
        }
        .confusion-header {
            background-color: #34495e !important;
            color: white;
            font-weight: bold;
            text-align: center;
        }
        .high-value {
            background-color: #d4edda;
            font-weight: bold;
        }
        .low-value {
            background-color: #f8d7da;
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <h1>Layout Detection Validation Report</h1>
""")

    # Summary metrics
    html_parts.append("""
    <h2>Overall Performance</h2>
    <div class="summary-grid">
        <div class="metric-card">
            <div class="metric-label">Mean Average Precision</div>
            <div class="metric-value">{:.3f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Images Processed</div>
            <div class="metric-value">{:,}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Avg Inference Time</div>
            <div class="metric-value">{:.1f} ms</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Total Time</div>
            <div class="metric-value">{:.1f} sec</div>
        </div>
    </div>
""".format(map_score, num_images, avg_time, total_time))

    # Per-class AP table
    html_parts.append("""
    <h2>Average Precision by Class</h2>
    <table>
        <thead>
            <tr>
                <th>Class ID</th>
                <th>Class Name</th>
                <th>Average Precision (AP)</th>
            </tr>
        </thead>
        <tbody>
""")

    # Sort by class ID
    for class_id in sorted(per_class_ap.keys()):
        class_name = DOCLAYNET_CLASS_MAPPING[class_id].value
        ap_value = per_class_ap[class_id]
        row_class = "high-value" if ap_value >= 0.7 else ("low-value" if ap_value < 0.5 else "")
        html_parts.append(f"""
            <tr class="{row_class}">
                <td>{class_id}</td>
                <td>{class_name}</td>
                <td>{ap_value:.3f}</td>
            </tr>
""")

    html_parts.append("""
        </tbody>
    </table>
""")

    # Per-class precision/recall/F1 table
    html_parts.append("""
    <h2>Per-Class Metrics</h2>
    <table>
        <thead>
            <tr>
                <th>Class ID</th>
                <th>Class Name</th>
                <th>Precision</th>
                <th>Recall</th>
                <th>F1 Score</th>
            </tr>
        </thead>
        <tbody>
""")

    for class_id in sorted(per_class_metrics.keys()):
        class_name = DOCLAYNET_CLASS_MAPPING[class_id].value
        metrics = per_class_metrics[class_id]
        precision = metrics["precision"]
        recall = metrics["recall"]
        f1 = metrics["f1"]

        # Highlight based on F1 score
        row_class = "high-value" if f1 >= 0.7 else ("low-value" if f1 < 0.5 else "")

        html_parts.append(f"""
            <tr class="{row_class}">
                <td>{class_id}</td>
                <td>{class_name}</td>
                <td>{precision:.3f}</td>
                <td>{recall:.3f}</td>
                <td>{f1:.3f}</td>
            </tr>
""")

    html_parts.append("""
        </tbody>
    </table>
""")

    # Confusion matrix
    html_parts.append("""
    <h2>Confusion Matrix</h2>
    <div class="confusion-matrix">
        <table>
            <thead>
                <tr>
                    <th class="confusion-header">True \\ Pred</th>
""")

    # Header row with predicted class IDs
    for class_id in range(confusion_matrix.shape[1]):
        html_parts.append(f'                    <th class="confusion-header">{class_id}</th>\n')

    html_parts.append("""
                </tr>
            </thead>
            <tbody>
""")

    # Confusion matrix rows
    for true_class in range(confusion_matrix.shape[0]):
        html_parts.append(f"""
                <tr>
                    <td class="confusion-header">{true_class}</td>
""")
        for pred_class in range(confusion_matrix.shape[1]):
            count = int(confusion_matrix[true_class, pred_class])
            # Highlight diagonal (correct predictions)
            cell_class = "high-value" if true_class == pred_class and count > 0 else ""
            html_parts.append(f'                    <td class="confusion-cell {cell_class}">{count}</td>\n')

        html_parts.append("""
                </tr>
""")

    html_parts.append("""
            </tbody>
        </table>
    </div>
""")

    # Footer
    html_parts.append("""
</body>
</html>
""")

    return "".join(html_parts)


def generate_csv_report(results: dict[str, Any], output_dir: Path) -> list[Path]:
    """
    Generate CSV reports from validation results.

    Creates three CSV files:
    1. {output_dir}/overall_metrics.csv - Overall mAP and timing
    2. {output_dir}/per_class_metrics.csv - Per-class AP, P, R, F1
    3. {output_dir}/confusion_matrix.csv - Confusion matrix

    Args:
        results: Validation results dictionary from validate_on_dataset()
        output_dir: Directory to save CSV files

    Returns:
        List of paths to created CSV files

    **Example:**
        ```python
        from pathlib import Path
        from project_b.evaluation import validate_on_dataset, generate_csv_report

        results = validate_on_dataset(detector, dataset_path, annotations_path)
        csv_files = generate_csv_report(results, Path("results"))

        print(f"Created {len(csv_files)} CSV files:")
        for csv_file in csv_files:
            print(f"  - {csv_file}")
        ```
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    created_files = []

    # 1. Overall metrics CSV
    overall_csv = output_dir / "overall_metrics.csv"
    with open(overall_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Metric", "Value"])
        writer.writerow(["mAP", f"{results['metrics']['mAP']:.4f}"])
        writer.writerow(["Num Images", results["num_images_processed"]])
        writer.writerow(["Avg Inference Time (ms)", f"{results['timing']['avg_inference_time_ms']:.2f}"])
        writer.writerow(["Total Time (sec)", f"{results['timing']['total_time_seconds']:.2f}"])
    created_files.append(overall_csv)

    # 2. Per-class metrics CSV
    per_class_csv = output_dir / "per_class_metrics.csv"
    with open(per_class_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Class ID", "Class Name", "AP", "Precision", "Recall", "F1"])

        per_class_ap = results["metrics"]["per_class_AP"]
        per_class_metrics = results["metrics"]["per_class_metrics"]

        for class_id in sorted(per_class_ap.keys()):
            class_name = DOCLAYNET_CLASS_MAPPING[class_id].value
            ap = per_class_ap[class_id]
            metrics = per_class_metrics[class_id]

            writer.writerow([
                class_id,
                class_name,
                f"{ap:.4f}",
                f"{metrics['precision']:.4f}",
                f"{metrics['recall']:.4f}",
                f"{metrics['f1']:.4f}",
            ])
    created_files.append(per_class_csv)

    # 3. Confusion matrix CSV
    confusion_csv = output_dir / "confusion_matrix.csv"
    confusion_matrix = np.array(results["metrics"]["confusion_matrix"])

    with open(confusion_csv, "w", newline="") as f:
        writer = csv.writer(f)

        # Header row
        header = ["True \\ Predicted"] + [str(i) for i in range(confusion_matrix.shape[1])]
        writer.writerow(header)

        # Data rows
        for true_class in range(confusion_matrix.shape[0]):
            row = [str(true_class)] + [str(int(confusion_matrix[true_class, pred_class]))
                                       for pred_class in range(confusion_matrix.shape[1])]
            writer.writerow(row)

    created_files.append(confusion_csv)

    return created_files


def save_report(
    results: dict[str, Any],
    output_path: Path,
    format: str = "auto",
) -> Path | list[Path]:
    """
    Save validation report to file(s).

    Automatically detects format from file extension or uses explicit format parameter.

    Args:
        results: Validation results dictionary from validate_on_dataset()
        output_path: Output file/directory path
        format: Report format ("auto", "json", "html", "csv")
            - "auto": Detect from extension (.json, .html, .csv)
            - "json": Save as JSON file
            - "html": Save as HTML file
            - "csv": Save as CSV files in directory

    Returns:
        Path to created file (json/html) or list of paths (csv)

    **Example:**
        ```python
        from pathlib import Path
        from project_b.evaluation import validate_on_dataset, save_report

        results = validate_on_dataset(detector, dataset_path, annotations_path)

        # Auto-detect from extension
        save_report(results, Path("report.html"))  # Creates HTML
        save_report(results, Path("report.json"))  # Creates JSON

        # Explicit format
        save_report(results, Path("results"), format="csv")  # Creates CSV dir
        ```
    """
    # Auto-detect format from extension
    if format == "auto":
        suffix = output_path.suffix.lower()
        if suffix == ".json":
            format = "json"
        elif suffix == ".html":
            format = "html"
        elif suffix == ".csv" or output_path.is_dir():
            format = "csv"
        else:
            raise ValueError(
                f"Cannot auto-detect format from path: {output_path}. "
                f"Use explicit format parameter or add extension (.json, .html, .csv)"
            )

    # Generate and save report
    if format == "json":
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        return output_path

    elif format == "html":
        html_content = generate_html_report(results)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(html_content)
        return output_path

    elif format == "csv":
        # For CSV, output_path should be a directory
        if output_path.suffix == ".csv":
            # Remove .csv extension to get directory
            output_path = output_path.with_suffix("")

        csv_files = generate_csv_report(results, output_path)
        return csv_files

    else:
        raise ValueError(
            f"Unsupported format: {format}. "
            f"Supported formats: 'json', 'html', 'csv', 'auto'"
        )
