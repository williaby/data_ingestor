"""
Benchmark report generation.

Generates comprehensive reports in multiple formats:
- HTML: Interactive reports with visualizations
- JSON: Machine-readable results
- CSV: Tabular data for analysis
"""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class BenchmarkReporter:
    """
    Generates benchmark reports in multiple formats.

    Creates comprehensive reports with visualizations, metrics tables,
    parser comparisons, and failure analysis.

    Example:
        >>> reporter = BenchmarkReporter(results)
        >>> reporter.generate_html("report.html")
        >>> reporter.generate_csv("metrics.csv")
    """

    def __init__(self, results: Dict):
        """
        Initialize reporter with benchmark results.

        Args:
            results: Results dictionary from BenchmarkOrchestrator.run()
        """
        self.results = results
        self.metadata = results.get("metadata", {})
        self.datasets = results.get("datasets", {})
        self.overall = results.get("overall", {})

    def generate_html(self, output_path: Path) -> Path:
        """
        Generate HTML report with visualizations.

        Args:
            output_path: Output file path

        Returns:
            Path to generated HTML file
        """
        logger.info(f"Generating HTML report: {output_path}")

        html = self._build_html_report()

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            f.write(html)

        logger.info(f"HTML report saved: {output_path}")
        return output_path

    def _build_html_report(self) -> str:
        """Build complete HTML report."""
        # Simple HTML report (Phase 1.5)
        # Phase 2 will add interactive charts with plotly/chart.js

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Benchmark Report - {self.metadata.get('timestamp', 'N/A')}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            margin: 0 0 10px 0;
            color: #333;
        }}
        .metadata {{
            color: #666;
            font-size: 14px;
        }}
        .section {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h2 {{
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }}
        h3 {{
            color: #555;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #4CAF50;
            color: white;
            font-weight: 600;
        }}
        tr:hover {{
            background: #f5f5f5;
        }}
        .metric-value {{
            font-weight: bold;
        }}
        .success {{
            color: #4CAF50;
        }}
        .warning {{
            color: #FF9800;
        }}
        .error {{
            color: #f44336;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: #f9f9f9;
            padding: 15px;
            border-radius: 4px;
            border-left: 4px solid #4CAF50;
        }}
        .stat-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 5px;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Benchmark Report</h1>
        <div class="metadata">
            <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Run Time:</strong> {self.metadata.get('timestamp', 'N/A')}</p>
            <p><strong>Datasets:</strong> {', '.join(self.metadata.get('datasets', []))}</p>
            <p><strong>Parsers:</strong> {', '.join(self.metadata.get('parsers', []))}</p>
            <p><strong>Workers:</strong> {self.metadata.get('workers', 'N/A')}</p>
        </div>
    </div>

    {self._build_overall_section()}
    {self._build_dataset_sections()}
    {self._build_parser_comparison()}
</body>
</html>
"""
        return html

    def _build_overall_section(self) -> str:
        """Build overall statistics section."""
        total_docs = self.overall.get("total_documents", 0)
        successful = self.overall.get("total_successful", 0)
        failed = self.overall.get("total_failed", 0)
        success_rate = self.overall.get("success_rate", 0.0)
        throughput = self.overall.get("throughput_docs_per_hour", 0.0)
        total_time = self.overall.get("total_time", 0.0)

        return f"""
    <div class="section">
        <h2>Overall Performance</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Documents</div>
                <div class="stat-value">{total_docs}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Successful</div>
                <div class="stat-value success">{successful}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Failed</div>
                <div class="stat-value error">{failed}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Success Rate</div>
                <div class="stat-value">{success_rate:.1%}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Throughput</div>
                <div class="stat-value">{throughput:.1f} docs/hr</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Time</div>
                <div class="stat-value">{total_time/60:.1f} min</div>
            </div>
        </div>
    </div>
"""

    def _build_dataset_sections(self) -> str:
        """Build sections for each dataset."""
        sections = []

        for dataset_name, dataset_data in self.datasets.items():
            parsers_data = dataset_data.get("parsers", {})

            if not parsers_data:
                continue

            section = f"""
    <div class="section">
        <h2>Dataset: {dataset_name.upper()}</h2>
"""

            for parser_name, parser_data in parsers_data.items():
                agg = parser_data.get("aggregated", {})

                section += f"""
        <h3>Parser: {parser_name}</h3>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
            <tr>
                <td>Total Documents</td>
                <td class="metric-value">{agg.get('total_documents', 0)}</td>
            </tr>
            <tr>
                <td>Success Rate</td>
                <td class="metric-value {'success' if agg.get('success_rate', 0) > 0.95 else 'warning'}">{agg.get('success_rate', 0):.1%}</td>
            </tr>
            <tr>
                <td>Avg Processing Time</td>
                <td class="metric-value">{agg.get('avg_processing_time', 0):.2f}s</td>
            </tr>
"""

                # Add mean metrics
                mean_metrics = agg.get("mean_metrics", {})
                for metric_name, value in mean_metrics.items():
                    section += f"""
            <tr>
                <td>{metric_name}</td>
                <td class="metric-value">{value:.4f}</td>
            </tr>
"""

                section += """
        </table>
"""

            section += """
    </div>
"""
            sections.append(section)

        return "\n".join(sections)

    def _build_parser_comparison(self) -> str:
        """Build parser comparison table."""
        # Collect metrics for comparison
        comparison_data = []

        for dataset_name, dataset_data in self.datasets.items():
            for parser_name, parser_data in dataset_data.get(
                "parsers", {}
            ).items():
                agg = parser_data.get("aggregated", {})
                comparison_data.append(
                    {
                        "dataset": dataset_name,
                        "parser": parser_name,
                        "success_rate": agg.get("success_rate", 0),
                        "avg_time": agg.get("avg_processing_time", 0),
                        "total_docs": agg.get("total_documents", 0),
                    }
                )

        if not comparison_data:
            return ""

        section = """
    <div class="section">
        <h2>Parser Comparison</h2>
        <table>
            <tr>
                <th>Dataset</th>
                <th>Parser</th>
                <th>Documents</th>
                <th>Success Rate</th>
                <th>Avg Time (s)</th>
            </tr>
"""

        for row in comparison_data:
            section += f"""
            <tr>
                <td>{row['dataset']}</td>
                <td>{row['parser']}</td>
                <td>{row['total_docs']}</td>
                <td class="{'success' if row['success_rate'] > 0.95 else 'warning'}">{row['success_rate']:.1%}</td>
                <td>{row['avg_time']:.2f}</td>
            </tr>
"""

        section += """
        </table>
    </div>
"""
        return section

    def generate_json(self, output_path: Path) -> Path:
        """
        Generate JSON report.

        Args:
            output_path: Output file path

        Returns:
            Path to generated JSON file
        """
        logger.info(f"Generating JSON report: {output_path}")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2)

        logger.info(f"JSON report saved: {output_path}")
        return output_path

    def generate_csv(self, output_path: Path) -> Path:
        """
        Generate CSV report with metrics.

        Args:
            output_path: Output file path

        Returns:
            Path to generated CSV file
        """
        logger.info(f"Generating CSV report: {output_path}")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Flatten results for CSV
        rows = []
        for dataset_name, dataset_data in self.datasets.items():
            for parser_name, parser_data in dataset_data.get(
                "parsers", {}
            ).items():
                agg = parser_data.get("aggregated", {})

                # Base row
                row = {
                    "dataset": dataset_name,
                    "parser": parser_name,
                    "total_documents": agg.get("total_documents", 0),
                    "successful_documents": agg.get("successful_documents", 0),
                    "failed_documents": agg.get("failed_documents", 0),
                    "success_rate": agg.get("success_rate", 0),
                    "avg_processing_time": agg.get("avg_processing_time", 0),
                }

                # Add mean metrics
                mean_metrics = agg.get("mean_metrics", {})
                for metric_name, value in mean_metrics.items():
                    row[f"mean_{metric_name}"] = value

                # Add std metrics
                std_metrics = agg.get("std_metrics", {})
                for metric_name, value in std_metrics.items():
                    row[f"std_{metric_name}"] = value

                rows.append(row)

        if rows:
            with open(output_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)

        logger.info(f"CSV report saved: {output_path}")
        return output_path
