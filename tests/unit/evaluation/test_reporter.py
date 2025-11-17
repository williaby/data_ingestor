"""
Unit tests for report generation.

Tests HTML and CSV report generation from validation results.
"""

import json
from pathlib import Path

import numpy as np
import pytest

from project_b.evaluation.reporter import (
    generate_csv_report,
    generate_html_report,
    save_report,
)


@pytest.fixture
def sample_validation_results():
    """Sample validation results for testing."""
    return {
        "metrics": {
            "mAP": 0.842,
            "per_class_AP": {
                0: 0.78,
                1: 0.65,
                2: 0.91,
                3: 0.82,
                4: 0.75,
                5: 0.70,
                6: 0.88,
                7: 0.85,
                8: 0.95,
                9: 0.80,
                10: 0.92,
            },
            "per_class_metrics": {
                0: {"precision": 0.80, "recall": 0.75, "f1": 0.77, "tp": 30, "fp": 8, "fn": 10},
                1: {"precision": 0.70, "recall": 0.60, "f1": 0.65, "tp": 12, "fp": 5, "fn": 8},
                2: {"precision": 0.92, "recall": 0.90, "f1": 0.91, "tp": 45, "fp": 4, "fn": 5},
                3: {"precision": 0.85, "recall": 0.80, "f1": 0.82, "tp": 32, "fp": 6, "fn": 8},
                4: {"precision": 0.78, "recall": 0.72, "f1": 0.75, "tp": 18, "fp": 5, "fn": 7},
                5: {"precision": 0.72, "recall": 0.68, "f1": 0.70, "tp": 20, "fp": 8, "fn": 10},
                6: {"precision": 0.90, "recall": 0.86, "f1": 0.88, "tp": 43, "fp": 5, "fn": 7},
                7: {"precision": 0.87, "recall": 0.83, "f1": 0.85, "tp": 50, "fp": 7, "fn": 10},
                8: {"precision": 0.96, "recall": 0.94, "f1": 0.95, "tp": 94, "fp": 4, "fn": 6},
                9: {"precision": 0.82, "recall": 0.78, "f1": 0.80, "tp": 156, "fp": 34, "fn": 44},
                10: {"precision": 0.94, "recall": 0.90, "f1": 0.92, "tp": 54, "fp": 3, "fn": 6},
            },
            "confusion_matrix": np.eye(11).tolist(),  # Perfect diagonal for simplicity
        },
        "num_images_processed": 100,
        "total_detections": 554,
        "total_ground_truths": 560,
        "timing": {
            "total_time_seconds": 125.5,
            "avg_inference_time_ms": 85.3,
            "inference_times_ms": [80.0, 85.0, 90.0] * 33 + [85.0],
        },
        "config": {
            "confidence_threshold": 0.3,
            "iou_threshold": 0.5,
            "nms_threshold": 0.45,
        },
    }


class TestHTMLReportGeneration:
    """Test HTML report generation."""

    def test_generate_html_report_structure(self, sample_validation_results):
        """Test that HTML report has correct structure."""
        html = generate_html_report(sample_validation_results)

        # Check basic HTML structure
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html
        assert "<head>" in html
        assert "<body>" in html

        # Check title
        assert "Layout Detection Validation Report" in html

        # Check metrics sections
        assert "Overall Performance" in html
        assert "Average Precision by Class" in html
        assert "Per-Class Metrics" in html
        assert "Confusion Matrix" in html

    def test_html_report_contains_metrics(self, sample_validation_results):
        """Test that HTML report contains key metrics."""
        html = generate_html_report(sample_validation_results)

        # Check mAP value
        assert "0.842" in html

        # Check number of images
        assert "100" in html

        # Check class names (sampling a few)
        assert "caption" in html or "CAPTION" in html.lower()
        assert "text" in html or "TEXT" in html.lower()
        assert "title" in html or "TITLE" in html.lower()

    def test_html_report_has_styling(self, sample_validation_results):
        """Test that HTML report includes CSS styling."""
        html = generate_html_report(sample_validation_results)

        # Check for CSS
        assert "<style>" in html
        assert "</style>" in html

        # Check for some style classes
        assert "table" in html
        assert "metric-card" in html

    def test_html_report_all_classes_present(self, sample_validation_results):
        """Test that all 11 DocLayNet classes appear in report."""
        html = generate_html_report(sample_validation_results)

        # All class IDs should be present
        for class_id in range(11):
            # Either as <td>0</td> or similar
            assert f"<td>{class_id}</td>" in html or f">{class_id}<" in html


class TestCSVReportGeneration:
    """Test CSV report generation."""

    def test_generate_csv_report_creates_files(self, sample_validation_results, tmp_path):
        """Test that CSV report creates expected files."""
        csv_files = generate_csv_report(sample_validation_results, tmp_path)

        assert len(csv_files) == 3
        assert all(f.exists() for f in csv_files)

        # Check file names
        file_names = [f.name for f in csv_files]
        assert "overall_metrics.csv" in file_names
        assert "per_class_metrics.csv" in file_names
        assert "confusion_matrix.csv" in file_names

    def test_overall_metrics_csv_content(self, sample_validation_results, tmp_path):
        """Test overall metrics CSV contains correct data."""
        csv_files = generate_csv_report(sample_validation_results, tmp_path)
        overall_csv = tmp_path / "overall_metrics.csv"

        assert overall_csv.exists()

        content = overall_csv.read_text()

        # Check header
        assert "Metric,Value" in content

        # Check mAP value
        assert "0.8420" in content

        # Check num images
        assert "100" in content

    def test_per_class_metrics_csv_content(self, sample_validation_results, tmp_path):
        """Test per-class metrics CSV contains correct data."""
        csv_files = generate_csv_report(sample_validation_results, tmp_path)
        per_class_csv = tmp_path / "per_class_metrics.csv"

        assert per_class_csv.exists()

        content = per_class_csv.read_text()

        # Check header
        assert "Class ID,Class Name,AP,Precision,Recall,F1" in content

        # Check some class data
        assert "0,caption" in content
        assert "9,text" in content
        assert "10,title" in content

        # Check some metric values
        assert "0.78" in content or "0.7800" in content  # Class 0 AP

    def test_confusion_matrix_csv_content(self, sample_validation_results, tmp_path):
        """Test confusion matrix CSV contains correct structure."""
        csv_files = generate_csv_report(sample_validation_results, tmp_path)
        cm_csv = tmp_path / "confusion_matrix.csv"

        assert cm_csv.exists()

        content = cm_csv.read_text()

        # Check header (should have True \ Predicted and 0-10)
        assert "True \\ Predicted" in content or "True" in content

        # Check that we have 11 classes (0-10)
        lines = content.strip().split("\n")
        # Header + 11 data rows
        assert len(lines) == 12


class TestSaveReport:
    """Test unified save_report function."""

    def test_save_report_auto_json(self, sample_validation_results, tmp_path):
        """Test auto-detection of JSON format from extension."""
        output_path = tmp_path / "report.json"
        saved_path = save_report(sample_validation_results, output_path, format="auto")

        assert saved_path == output_path
        assert output_path.exists()

        # Verify it's valid JSON
        with open(output_path) as f:
            data = json.load(f)
            assert data["metrics"]["mAP"] == 0.842

    def test_save_report_auto_html(self, sample_validation_results, tmp_path):
        """Test auto-detection of HTML format from extension."""
        output_path = tmp_path / "report.html"
        saved_path = save_report(sample_validation_results, output_path, format="auto")

        assert saved_path == output_path
        assert output_path.exists()

        content = output_path.read_text()
        assert "<!DOCTYPE html>" in content

    def test_save_report_auto_csv(self, sample_validation_results, tmp_path):
        """Test auto-detection of CSV format from extension."""
        output_path = tmp_path / "report.csv"
        saved_paths = save_report(sample_validation_results, output_path, format="auto")

        # CSV returns list of files
        assert isinstance(saved_paths, list)
        assert len(saved_paths) == 3

        # Check directory was created (without .csv extension)
        csv_dir = tmp_path / "report"
        assert csv_dir.exists()
        assert csv_dir.is_dir()

    def test_save_report_explicit_json(self, sample_validation_results, tmp_path):
        """Test explicit JSON format."""
        output_path = tmp_path / "report.txt"  # Wrong extension
        saved_path = save_report(sample_validation_results, output_path, format="json")

        assert saved_path == output_path
        assert output_path.exists()

        # Should still be JSON despite .txt extension
        with open(output_path) as f:
            data = json.load(f)
            assert "mAP" in data["metrics"]

    def test_save_report_explicit_html(self, sample_validation_results, tmp_path):
        """Test explicit HTML format."""
        output_path = tmp_path / "report.txt"  # Wrong extension
        saved_path = save_report(sample_validation_results, output_path, format="html")

        assert saved_path == output_path
        assert output_path.exists()

        content = output_path.read_text()
        assert "<!DOCTYPE html>" in content

    def test_save_report_explicit_csv(self, sample_validation_results, tmp_path):
        """Test explicit CSV format."""
        output_path = tmp_path / "results"
        saved_paths = save_report(sample_validation_results, output_path, format="csv")

        assert isinstance(saved_paths, list)
        assert len(saved_paths) == 3
        assert all(p.exists() for p in saved_paths)

    def test_save_report_invalid_format(self, sample_validation_results, tmp_path):
        """Test error on invalid format."""
        output_path = tmp_path / "report.xyz"

        with pytest.raises(ValueError, match="Cannot auto-detect format"):
            save_report(sample_validation_results, output_path, format="auto")

        with pytest.raises(ValueError, match="Unsupported format"):
            save_report(sample_validation_results, output_path, format="invalid")

    def test_save_report_creates_parent_directories(self, sample_validation_results, tmp_path):
        """Test that save_report creates parent directories if they don't exist."""
        output_path = tmp_path / "subdir1" / "subdir2" / "report.json"
        saved_path = save_report(sample_validation_results, output_path, format="json")

        assert saved_path == output_path
        assert output_path.exists()
        assert output_path.parent.exists()
