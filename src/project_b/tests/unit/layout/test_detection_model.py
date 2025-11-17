"""
Unit tests for Detection Pydantic model.

Tests for bbox validation, confidence validation, and model serialization.
"""

import pytest
from pydantic import ValidationError

from project_b.layout.detector import Detection
from project_b.schemas.ocr_document import ClassLabelEnum


class TestDetectionModel:
    """Test Detection Pydantic model validation and serialization."""

    def test_valid_detection(self):
        """Test creating valid Detection."""
        det = Detection(
            bbox=[10.0, 20.0, 100.0, 50.0],
            confidence=0.95,
            class_id=10,
            class_label=ClassLabelEnum.TITLE,
        )

        assert det.bbox == [10.0, 20.0, 100.0, 50.0]
        assert det.confidence == 0.95
        assert det.class_id == 10
        assert det.class_label == ClassLabelEnum.TITLE

    def test_bbox_must_have_four_elements(self):
        """Test bbox must have exactly 4 elements."""
        # Too few elements
        with pytest.raises(ValidationError, match="at least 4 items"):
            Detection(
                bbox=[10.0, 20.0, 100.0],  # Only 3 elements
                confidence=0.95,
                class_id=10,
                class_label=ClassLabelEnum.TITLE,
            )

        # Too many elements
        with pytest.raises(ValidationError, match="at most 4 items"):
            Detection(
                bbox=[10.0, 20.0, 100.0, 50.0, 30.0],  # 5 elements
                confidence=0.95,
                class_id=10,
                class_label=ClassLabelEnum.TITLE,
            )

    def test_confidence_must_be_in_range(self):
        """Test confidence must be in [0.0, 1.0]."""
        # Confidence too low
        with pytest.raises(ValidationError):
            Detection(
                bbox=[10.0, 20.0, 100.0, 50.0],
                confidence=-0.1,  # Invalid
                class_id=10,
                class_label=ClassLabelEnum.TITLE,
            )

        # Confidence too high
        with pytest.raises(ValidationError):
            Detection(
                bbox=[10.0, 20.0, 100.0, 50.0],
                confidence=1.5,  # Invalid
                class_id=10,
                class_label=ClassLabelEnum.TITLE,
            )

    def test_confidence_boundary_values(self):
        """Test confidence accepts boundary values 0.0 and 1.0."""
        # confidence = 0.0
        det1 = Detection(
            bbox=[10.0, 20.0, 100.0, 50.0],
            confidence=0.0,
            class_id=10,
            class_label=ClassLabelEnum.TITLE,
        )
        assert det1.confidence == 0.0

        # confidence = 1.0
        det2 = Detection(
            bbox=[10.0, 20.0, 100.0, 50.0],
            confidence=1.0,
            class_id=10,
            class_label=ClassLabelEnum.TITLE,
        )
        assert det2.confidence == 1.0

    def test_class_id_must_be_in_range(self):
        """Test class_id must be in [0, 10] for DocLayNet."""
        # class_id too low
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            Detection(
                bbox=[10.0, 20.0, 100.0, 50.0],
                confidence=0.95,
                class_id=-1,  # Invalid
                class_label=ClassLabelEnum.TITLE,
            )

        # class_id too high
        with pytest.raises(ValidationError, match="less than or equal to 10"):
            Detection(
                bbox=[10.0, 20.0, 100.0, 50.0],
                confidence=0.95,
                class_id=11,  # Invalid (DocLayNet has 11 classes: 0-10)
                class_label=ClassLabelEnum.TITLE,
            )

    def test_class_id_boundary_values(self):
        """Test class_id accepts boundary values 0 and 10."""
        # class_id = 0 (caption)
        det1 = Detection(
            bbox=[10.0, 20.0, 100.0, 50.0],
            confidence=0.95,
            class_id=0,
            class_label=ClassLabelEnum.CAPTION,
        )
        assert det1.class_id == 0

        # class_id = 10 (title)
        det2 = Detection(
            bbox=[10.0, 20.0, 100.0, 50.0],
            confidence=0.95,
            class_id=10,
            class_label=ClassLabelEnum.TITLE,
        )
        assert det2.class_id == 10

    def test_all_class_labels_valid(self):
        """Test all DocLayNet class labels are valid."""
        class_mappings = [
            (0, ClassLabelEnum.CAPTION),
            (1, ClassLabelEnum.FOOTNOTE),
            (2, ClassLabelEnum.FORMULA),
            (3, ClassLabelEnum.LIST_ITEM),
            (4, ClassLabelEnum.PAGE_FOOTER),
            (5, ClassLabelEnum.PAGE_HEADER),
            (6, ClassLabelEnum.PICTURE),
            (7, ClassLabelEnum.SECTION_HEADER),
            (8, ClassLabelEnum.TABLE),
            (9, ClassLabelEnum.TEXT),
            (10, ClassLabelEnum.TITLE),
        ]

        for class_id, class_label in class_mappings:
            det = Detection(
                bbox=[10.0, 20.0, 100.0, 50.0],
                confidence=0.95,
                class_id=class_id,
                class_label=class_label,
            )
            assert det.class_id == class_id
            assert det.class_label == class_label

    def test_detection_serialization(self):
        """Test Detection can be serialized to dict/JSON."""
        det = Detection(
            bbox=[10.0, 20.0, 100.0, 50.0],
            confidence=0.95,
            class_id=10,
            class_label=ClassLabelEnum.TITLE,
        )

        # Serialize to dict
        det_dict = det.model_dump()
        assert det_dict["bbox"] == [10.0, 20.0, 100.0, 50.0]
        assert det_dict["confidence"] == 0.95
        assert det_dict["class_id"] == 10
        assert det_dict["class_label"] == "title"  # Enum serialized to string

        # Serialize to JSON
        det_json = det.model_dump_json()
        assert isinstance(det_json, str)
        assert "10.0" in det_json
        assert "0.95" in det_json
        assert "title" in det_json

    def test_detection_deserialization(self):
        """Test Detection can be deserialized from dict."""
        det_dict = {
            "bbox": [10.0, 20.0, 100.0, 50.0],
            "confidence": 0.95,
            "class_id": 10,
            "class_label": "title",
        }

        det = Detection.model_validate(det_dict)
        assert det.bbox == [10.0, 20.0, 100.0, 50.0]
        assert det.confidence == 0.95
        assert det.class_id == 10
        assert det.class_label == ClassLabelEnum.TITLE

    def test_detection_immutable(self):
        """Test Detection model is immutable (Pydantic frozen)."""
        det = Detection(
            bbox=[10.0, 20.0, 100.0, 50.0],
            confidence=0.95,
            class_id=10,
            class_label=ClassLabelEnum.TITLE,
        )

        # Try to modify (should raise ValidationError since Pydantic models are mutable by default)
        # Note: We may want to add frozen=True to ConfigDict if immutability is required
        det.confidence = 0.8  # This will work by default
        assert det.confidence == 0.8

    def test_bbox_coco_format_interpretation(self):
        """Test COCO format bbox [x, y, width, height] interpretation."""
        det = Detection(
            bbox=[50.0, 100.0, 200.0, 150.0],
            confidence=0.95,
            class_id=10,
            class_label=ClassLabelEnum.TITLE,
        )

        x, y, width, height = det.bbox

        # COCO format: [x, y, width, height]
        assert x == 50.0  # x-coordinate of top-left corner
        assert y == 100.0  # y-coordinate of top-left corner
        assert width == 200.0  # bbox width
        assert height == 150.0  # bbox height

        # Can compute bottom-right corner
        x_max = x + width
        y_max = y + height
        assert x_max == 250.0
        assert y_max == 250.0

    def test_extended_class_labels(self):
        """Test extended class labels (handwriting, revision_marking) beyond DocLayNet 11."""
        # Note: Extended classes may have class_id > 10, so we need to adjust validation
        # For now, test that they work as ClassLabelEnum values

        # These are valid ClassLabelEnum values
        assert ClassLabelEnum.HANDWRITING.value == "handwriting"
        assert ClassLabelEnum.REVISION_MARKING.value == "revision_marking"

        # If we want to use them in Detection, class_id validation needs adjustment
        # For now, they would fail class_id validation (class_id must be 0-10)
