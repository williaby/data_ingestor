"""
Unit tests for validation framework.

Tests COCO annotation loading, annotation conversion, and validation workflow.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from project_b.layout.detector import ClassLabelEnum, Detection, YOLODetector
from project_b.evaluation.validator import (
    coco_annotation_to_detection,
    load_coco_annotations,
    print_validation_summary,
    validate_on_dataset,
)


@pytest.fixture
def sample_coco_annotations(tmp_path):
    """Create sample COCO format annotations file."""
    coco_data = {
        "images": [
            {
                "id": 1,
                "file_name": "image_001.png",
                "width": 1024,
                "height": 1024,
            },
            {
                "id": 2,
                "file_name": "image_002.png",
                "width": 1024,
                "height": 1024,
            },
        ],
        "annotations": [
            # Image 1: 2 annotations
            {
                "id": 1,
                "image_id": 1,
                "category_id": 9,  # text
                "bbox": [10.0, 10.0, 100.0, 50.0],
                "area": 5000.0,
            },
            {
                "id": 2,
                "image_id": 1,
                "category_id": 10,  # title
                "bbox": [10.0, 70.0, 100.0, 30.0],
                "area": 3000.0,
            },
            # Image 2: 1 annotation
            {
                "id": 3,
                "image_id": 2,
                "category_id": 8,  # table
                "bbox": [50.0, 50.0, 200.0, 150.0],
                "area": 30000.0,
            },
        ],
        "categories": [
            {"id": i, "name": f"class_{i}"} for i in range(11)
        ],
    }

    annotations_file = tmp_path / "annotations.json"
    with open(annotations_file, "w") as f:
        json.dump(coco_data, f)

    return annotations_file


@pytest.fixture
def sample_dataset_images(tmp_path):
    """Create sample dataset images."""
    dataset_path = tmp_path / "dataset"
    dataset_path.mkdir()

    # Create two dummy images
    for i in [1, 2]:
        img = Image.new("RGB", (1024, 1024), color="white")
        img.save(dataset_path / f"image_{i:03d}.png")

    return dataset_path


class TestLoadCOCOAnnotations:
    """Test COCO annotation loading."""

    def test_load_annotations_success(self, sample_coco_annotations):
        """Test successful loading of COCO annotations."""
        images_dict, annotations_dict = load_coco_annotations(sample_coco_annotations)

        # Check images dict
        assert len(images_dict) == 2
        assert 1 in images_dict
        assert 2 in images_dict
        assert images_dict[1]["file_name"] == "image_001.png"
        assert images_dict[2]["file_name"] == "image_002.png"

        # Check annotations dict
        assert len(annotations_dict) == 2
        assert 1 in annotations_dict
        assert 2 in annotations_dict
        assert len(annotations_dict[1]) == 2  # Image 1 has 2 annotations
        assert len(annotations_dict[2]) == 1  # Image 2 has 1 annotation

    def test_load_annotations_file_not_found(self, tmp_path):
        """Test error when annotations file doesn't exist."""
        nonexistent_file = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            load_coco_annotations(nonexistent_file)

    def test_load_annotations_missing_images_key(self, tmp_path):
        """Test error when annotations JSON missing 'images' key."""
        bad_file = tmp_path / "bad.json"
        with open(bad_file, "w") as f:
            json.dump({"annotations": []}, f)

        with pytest.raises(KeyError, match="images"):
            load_coco_annotations(bad_file)

    def test_load_annotations_missing_annotations_key(self, tmp_path):
        """Test error when annotations JSON missing 'annotations' key."""
        bad_file = tmp_path / "bad.json"
        with open(bad_file, "w") as f:
            json.dump({"images": []}, f)

        with pytest.raises(KeyError, match="annotations"):
            load_coco_annotations(bad_file)


class TestCOCOAnnotationToDetection:
    """Test COCO annotation to Detection conversion."""

    def test_convert_annotation_success(self):
        """Test successful conversion of COCO annotation."""
        coco_ann = {
            "id": 1,
            "image_id": 1,
            "category_id": 9,
            "bbox": [10.0, 20.0, 100.0, 50.0],
            "area": 5000.0,
        }

        detection = coco_annotation_to_detection(coco_ann)

        assert isinstance(detection, Detection)
        assert detection.bbox == [10.0, 20.0, 100.0, 50.0]
        assert detection.confidence == 1.0  # Ground truth has confidence 1.0
        assert detection.class_id == 9
        assert detection.class_label == ClassLabelEnum.TEXT

    def test_convert_all_class_ids(self):
        """Test conversion for all 11 DocLayNet classes."""
        for class_id in range(11):
            coco_ann = {
                "id": 1,
                "image_id": 1,
                "category_id": class_id,
                "bbox": [10.0, 10.0, 50.0, 50.0],
            }

            detection = coco_annotation_to_detection(coco_ann)

            assert detection.class_id == class_id
            # Just check it doesn't raise an error for valid class IDs

    def test_convert_invalid_class_id(self):
        """Test error on invalid class ID."""
        coco_ann = {
            "id": 1,
            "image_id": 1,
            "category_id": 99,  # Invalid class ID
            "bbox": [10.0, 10.0, 50.0, 50.0],
        }

        with pytest.raises(KeyError):
            coco_annotation_to_detection(coco_ann)


class TestValidateOnDataset:
    """Test end-to-end validation workflow."""

    @patch("project_b.evaluation.validator.YOLODetector")
    def test_validate_basic_workflow(
        self,
        mock_detector_class,
        sample_coco_annotations,
        sample_dataset_images,
    ):
        """Test basic validation workflow with mocked detector."""
        # Create mock detector
        mock_detector = MagicMock(spec=YOLODetector)

        # Mock detect() to return synthetic detections
        def mock_detect(image, confidence_threshold=0.3):
            # Return one detection per image
            return [
                Detection(
                    bbox=[10.0, 10.0, 100.0, 50.0],
                    confidence=0.9,
                    class_id=9,
                    class_label=ClassLabelEnum.TEXT,
                )
            ]

        mock_detector.detect.side_effect = mock_detect

        # Run validation
        results = validate_on_dataset(
            detector=mock_detector,
            dataset_path=sample_dataset_images,
            annotations_path=sample_coco_annotations,
            confidence_threshold=0.3,
            iou_threshold=0.5,
            nms_threshold=0.45,
            verbose=False,
        )

        # Check results structure
        assert "metrics" in results
        assert "mAP" in results["metrics"]
        assert "per_class_AP" in results["metrics"]
        assert "per_class_metrics" in results["metrics"]
        assert "confusion_matrix" in results["metrics"]
        assert "timing" in results
        assert "num_images_processed" in results

        # Check that detector was called for each image
        assert mock_detector.detect.call_count == 2

    @patch("project_b.evaluation.validator.YOLODetector")
    def test_validate_max_images_limit(
        self,
        mock_detector_class,
        sample_coco_annotations,
        sample_dataset_images,
    ):
        """Test that max_images parameter limits processing."""
        mock_detector = MagicMock(spec=YOLODetector)
        mock_detector.detect.return_value = []

        # Run validation with max_images=1
        results = validate_on_dataset(
            detector=mock_detector,
            dataset_path=sample_dataset_images,
            annotations_path=sample_coco_annotations,
            max_images=1,
            verbose=False,
        )

        # Should only process 1 image
        assert results["num_images_processed"] == 1
        assert mock_detector.detect.call_count == 1

    @patch("project_b.evaluation.validator.YOLODetector")
    def test_validate_timing_metrics(
        self,
        mock_detector_class,
        sample_coco_annotations,
        sample_dataset_images,
    ):
        """Test that timing metrics are recorded."""
        mock_detector = MagicMock(spec=YOLODetector)
        mock_detector.detect.return_value = []

        results = validate_on_dataset(
            detector=mock_detector,
            dataset_path=sample_dataset_images,
            annotations_path=sample_coco_annotations,
            verbose=False,
        )

        # Check timing metrics
        assert "timing" in results
        assert "total_time_seconds" in results["timing"]
        assert "avg_inference_time_ms" in results["timing"]
        assert "inference_times_ms" in results["timing"]

        # Should have timing for 2 images
        assert len(results["timing"]["inference_times_ms"]) == 2

    @patch("project_b.evaluation.validator.YOLODetector")
    def test_validate_config_stored(
        self,
        mock_detector_class,
        sample_coco_annotations,
        sample_dataset_images,
    ):
        """Test that validation config is stored in results."""
        mock_detector = MagicMock(spec=YOLODetector)
        mock_detector.detect.return_value = []

        results = validate_on_dataset(
            detector=mock_detector,
            dataset_path=sample_dataset_images,
            annotations_path=sample_coco_annotations,
            confidence_threshold=0.4,
            iou_threshold=0.6,
            nms_threshold=0.5,
            verbose=False,
        )

        # Check config stored
        assert "config" in results
        assert results["config"]["confidence_threshold"] == 0.4
        assert results["config"]["iou_threshold"] == 0.6
        assert results["config"]["nms_threshold"] == 0.5

    @patch("project_b.evaluation.validator.YOLODetector")
    def test_validate_no_annotations_for_image(
        self,
        mock_detector_class,
        tmp_path,
    ):
        """Test validation when an image has no annotations."""
        # Create annotations with image but no annotations for it
        coco_data = {
            "images": [
                {"id": 1, "file_name": "image_001.png", "width": 1024, "height": 1024},
            ],
            "annotations": [],  # No annotations
            "categories": [{"id": i, "name": f"class_{i}"} for i in range(11)],
        }

        annotations_file = tmp_path / "annotations.json"
        with open(annotations_file, "w") as f:
            json.dump(coco_data, f)

        # Create dataset image
        dataset_path = tmp_path / "dataset"
        dataset_path.mkdir()
        img = Image.new("RGB", (1024, 1024), color="white")
        img.save(dataset_path / "image_001.png")

        # Mock detector
        mock_detector = MagicMock(spec=YOLODetector)
        mock_detector.detect.return_value = []

        # Should not raise error
        results = validate_on_dataset(
            detector=mock_detector,
            dataset_path=dataset_path,
            annotations_path=annotations_file,
            verbose=False,
        )

        assert results["num_images_processed"] == 1
        assert results["total_ground_truths"] == 0


class TestPrintValidationSummary:
    """Test validation summary printing."""

    def test_print_summary_no_error(self, capsys):
        """Test that print_validation_summary doesn't raise errors."""
        results = {
            "metrics": {
                "mAP": 0.85,
                "per_class_AP": {0: 0.8, 1: 0.75, 2: 0.9},
                "per_class_metrics": {
                    0: {"precision": 0.8, "recall": 0.75, "f1": 0.77, "tp": 10, "fp": 2, "fn": 3},
                    1: {"precision": 0.75, "recall": 0.7, "f1": 0.72, "tp": 7, "fp": 2, "fn": 3},
                },
                "confusion_matrix": np.eye(11).tolist(),
            },
            "num_images_processed": 50,
            "total_detections": 100,
            "total_ground_truths": 95,
            "timing": {
                "total_time_seconds": 45.5,
                "avg_inference_time_ms": 90.5,
                "inference_times_ms": [85.0, 90.0, 95.0],
            },
            "config": {
                "confidence_threshold": 0.3,
                "iou_threshold": 0.5,
                "nms_threshold": 0.45,
            },
        }

        # Should not raise error
        print_validation_summary(results)

        # Capture output
        captured = capsys.readouterr()

        # Check some key output
        assert "VALIDATION RESULTS" in captured.out
        assert "mAP" in captured.out
        assert "0.850" in captured.out or "0.85" in captured.out

    def test_print_summary_contains_all_sections(self, capsys):
        """Test that summary contains all expected sections."""
        results = {
            "metrics": {
                "mAP": 0.85,
                "per_class_AP": {9: 0.8},
                "per_class_metrics": {
                    9: {"precision": 0.8, "recall": 0.75, "f1": 0.77, "tp": 10, "fp": 2, "fn": 3},
                },
                "confusion_matrix": np.eye(11).tolist(),
            },
            "num_images_processed": 50,
            "total_detections": 100,
            "total_ground_truths": 95,
            "timing": {
                "total_time_seconds": 45.5,
                "avg_inference_time_ms": 90.5,
                "inference_times_ms": [85.0],
            },
            "config": {
                "confidence_threshold": 0.3,
                "iou_threshold": 0.5,
                "nms_threshold": 0.45,
            },
        }

        print_validation_summary(results)

        captured = capsys.readouterr()

        # Check sections
        assert "Per-Class Average Precision" in captured.out
        assert "Per-Class Precision/Recall/F1" in captured.out
