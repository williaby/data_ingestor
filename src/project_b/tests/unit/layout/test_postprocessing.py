"""
Unit tests for layout detection postprocessing utilities.

Tests for NMS, filtering, reading order assignment, and bbox operations.
"""

import pytest

from project_b.layout.detector import Detection
from project_b.layout.postprocessing import (
    apply_nms,
    assign_reading_order,
    compute_iou,
    filter_by_confidence,
    filter_by_size,
    remove_overlapping_classes,
)
from project_b.schemas.ocr_document import ClassLabelEnum


class TestComputeIoU:
    """Test IoU computation for COCO format bboxes."""

    def test_identical_bboxes(self):
        """Test IoU = 1.0 for identical bboxes."""
        bbox1 = [10.0, 10.0, 100.0, 100.0]
        bbox2 = [10.0, 10.0, 100.0, 100.0]
        iou = compute_iou(bbox1, bbox2)
        assert iou == 1.0

    def test_no_overlap(self):
        """Test IoU = 0.0 for non-overlapping bboxes."""
        bbox1 = [0.0, 0.0, 50.0, 50.0]
        bbox2 = [100.0, 100.0, 50.0, 50.0]
        iou = compute_iou(bbox1, bbox2)
        assert iou == 0.0

    def test_partial_overlap(self):
        """Test IoU for partially overlapping bboxes."""
        bbox1 = [0.0, 0.0, 100.0, 100.0]  # Area = 10000
        bbox2 = [50.0, 50.0, 100.0, 100.0]  # Area = 10000
        # Intersection: 50x50 = 2500
        # Union: 10000 + 10000 - 2500 = 17500
        # IoU = 2500 / 17500 = 0.142857...
        iou = compute_iou(bbox1, bbox2)
        assert abs(iou - 0.142857) < 0.001

    def test_one_bbox_inside_another(self):
        """Test IoU when one bbox is completely inside another."""
        bbox1 = [0.0, 0.0, 200.0, 200.0]  # Large bbox
        bbox2 = [50.0, 50.0, 50.0, 50.0]  # Small bbox inside
        # Intersection: 50x50 = 2500
        # Union: 40000 (large area, small bbox contained)
        iou = compute_iou(bbox1, bbox2)
        # Small bbox area / Large bbox area = 2500 / 40000 = 0.0625
        assert abs(iou - 0.0625) < 0.001

    def test_zero_area_bbox(self):
        """Test IoU = 0.0 when one bbox has zero area."""
        bbox1 = [10.0, 10.0, 0.0, 0.0]  # Zero area
        bbox2 = [10.0, 10.0, 100.0, 100.0]
        iou = compute_iou(bbox1, bbox2)
        assert iou == 0.0


class TestApplyNMS:
    """Test Non-Maximum Suppression."""

    def test_empty_detections(self):
        """Test NMS with empty detection list."""
        result = apply_nms([], iou_threshold=0.5)
        assert result == []

    def test_single_detection(self):
        """Test NMS with single detection."""
        det = Detection(
            bbox=[10.0, 10.0, 100.0, 100.0],
            confidence=0.9,
            class_id=9,
            class_label=ClassLabelEnum.TEXT,
        )
        result = apply_nms([det], iou_threshold=0.5)
        assert len(result) == 1
        assert result[0] == det

    def test_duplicate_detections_same_class(self):
        """Test NMS removes duplicate detections of same class."""
        det1 = Detection(
            bbox=[10.0, 10.0, 100.0, 100.0],
            confidence=0.9,
            class_id=9,
            class_label=ClassLabelEnum.TEXT,
        )
        det2 = Detection(
            bbox=[15.0, 15.0, 100.0, 100.0],  # High overlap with det1
            confidence=0.8,  # Lower confidence
            class_id=9,
            class_label=ClassLabelEnum.TEXT,
        )

        result = apply_nms([det1, det2], iou_threshold=0.45)

        # Should keep only det1 (higher confidence)
        assert len(result) == 1
        assert result[0] == det1

    def test_different_classes_kept(self):
        """Test NMS keeps detections from different classes even if overlapping."""
        det1 = Detection(
            bbox=[10.0, 10.0, 100.0, 100.0],
            confidence=0.9,
            class_id=10,
            class_label=ClassLabelEnum.TITLE,
        )
        det2 = Detection(
            bbox=[15.0, 15.0, 100.0, 100.0],  # High overlap with det1
            confidence=0.8,
            class_id=9,
            class_label=ClassLabelEnum.TEXT,
        )

        result = apply_nms([det1, det2], iou_threshold=0.45)

        # Should keep both (different classes)
        assert len(result) == 2
        assert det1 in result
        assert det2 in result

    def test_multiple_duplicates(self):
        """Test NMS with multiple overlapping detections."""
        detections = [
            Detection(
                bbox=[10.0, 10.0, 100.0, 100.0],
                confidence=0.95,
                class_id=9,
                class_label=ClassLabelEnum.TEXT,
            ),
            Detection(
                bbox=[15.0, 15.0, 100.0, 100.0],
                confidence=0.90,
                class_id=9,
                class_label=ClassLabelEnum.TEXT,
            ),
            Detection(
                bbox=[20.0, 20.0, 100.0, 100.0],
                confidence=0.85,
                class_id=9,
                class_label=ClassLabelEnum.TEXT,
            ),
        ]

        result = apply_nms(detections, iou_threshold=0.45)

        # Should keep only highest confidence detection
        assert len(result) == 1
        assert result[0].confidence == 0.95

    def test_no_overlap_keeps_all(self):
        """Test NMS keeps all detections when no overlap."""
        detections = [
            Detection(
                bbox=[0.0, 0.0, 50.0, 50.0],
                confidence=0.9,
                class_id=9,
                class_label=ClassLabelEnum.TEXT,
            ),
            Detection(
                bbox=[100.0, 100.0, 50.0, 50.0],
                confidence=0.8,
                class_id=9,
                class_label=ClassLabelEnum.TEXT,
            ),
        ]

        result = apply_nms(detections, iou_threshold=0.45)

        # Should keep both (no overlap)
        assert len(result) == 2


class TestFilterByConfidence:
    """Test confidence-based filtering."""

    def test_empty_detections(self):
        """Test filtering with empty list."""
        result = filter_by_confidence([], min_confidence=0.5)
        assert result == []

    def test_all_above_threshold(self):
        """Test when all detections above threshold."""
        detections = [
            Detection(
                bbox=[10.0, 10.0, 100.0, 100.0],
                confidence=0.9,
                class_id=9,
                class_label=ClassLabelEnum.TEXT,
            ),
            Detection(
                bbox=[200.0, 200.0, 100.0, 100.0],
                confidence=0.8,
                class_id=10,
                class_label=ClassLabelEnum.TITLE,
            ),
        ]

        result = filter_by_confidence(detections, min_confidence=0.5)
        assert len(result) == 2

    def test_filtering_low_confidence(self):
        """Test filtering removes low confidence detections."""
        detections = [
            Detection(
                bbox=[10.0, 10.0, 100.0, 100.0],
                confidence=0.9,
                class_id=9,
                class_label=ClassLabelEnum.TEXT,
            ),
            Detection(
                bbox=[200.0, 200.0, 100.0, 100.0],
                confidence=0.4,  # Below threshold
                class_id=10,
                class_label=ClassLabelEnum.TITLE,
            ),
        ]

        result = filter_by_confidence(detections, min_confidence=0.5)
        assert len(result) == 1
        assert result[0].confidence == 0.9

    def test_exact_threshold(self):
        """Test detection at exact threshold is kept."""
        det = Detection(
            bbox=[10.0, 10.0, 100.0, 100.0],
            confidence=0.5,
            class_id=9,
            class_label=ClassLabelEnum.TEXT,
        )

        result = filter_by_confidence([det], min_confidence=0.5)
        assert len(result) == 1


class TestFilterBySize:
    """Test size-based filtering."""

    def test_empty_detections(self):
        """Test filtering with empty list."""
        result = filter_by_size([])
        assert result == []

    def test_all_above_threshold(self):
        """Test when all detections above size threshold."""
        detections = [
            Detection(
                bbox=[10.0, 10.0, 100.0, 100.0],
                confidence=0.9,
                class_id=9,
                class_label=ClassLabelEnum.TEXT,
            ),
            Detection(
                bbox=[200.0, 200.0, 50.0, 50.0],
                confidence=0.8,
                class_id=10,
                class_label=ClassLabelEnum.TITLE,
            ),
        ]

        result = filter_by_size(detections, min_width=20.0, min_height=20.0)
        assert len(result) == 2

    def test_filter_small_width(self):
        """Test filtering removes detections with small width."""
        detections = [
            Detection(
                bbox=[10.0, 10.0, 100.0, 100.0],
                confidence=0.9,
                class_id=9,
                class_label=ClassLabelEnum.TEXT,
            ),
            Detection(
                bbox=[200.0, 200.0, 5.0, 100.0],  # Width too small
                confidence=0.8,
                class_id=10,
                class_label=ClassLabelEnum.TITLE,
            ),
        ]

        result = filter_by_size(detections, min_width=10.0, min_height=10.0)
        assert len(result) == 1
        assert result[0].bbox[2] == 100.0  # width = 100

    def test_filter_small_height(self):
        """Test filtering removes detections with small height."""
        detections = [
            Detection(
                bbox=[10.0, 10.0, 100.0, 100.0],
                confidence=0.9,
                class_id=9,
                class_label=ClassLabelEnum.TEXT,
            ),
            Detection(
                bbox=[200.0, 200.0, 100.0, 5.0],  # Height too small
                confidence=0.8,
                class_id=10,
                class_label=ClassLabelEnum.TITLE,
            ),
        ]

        result = filter_by_size(detections, min_width=10.0, min_height=10.0)
        assert len(result) == 1
        assert result[0].bbox[3] == 100.0  # height = 100

    def test_filter_by_area(self):
        """Test filtering by minimum area."""
        detections = [
            Detection(
                bbox=[10.0, 10.0, 100.0, 100.0],  # Area = 10000
                confidence=0.9,
                class_id=9,
                class_label=ClassLabelEnum.TEXT,
            ),
            Detection(
                bbox=[200.0, 200.0, 10.0, 10.0],  # Area = 100
                confidence=0.8,
                class_id=10,
                class_label=ClassLabelEnum.TITLE,
            ),
        ]

        result = filter_by_size(detections, min_width=1.0, min_height=1.0, min_area=500.0)
        assert len(result) == 1
        assert result[0].bbox[2] * result[0].bbox[3] == 10000  # Area check


class TestAssignReadingOrder:
    """Test reading order assignment."""

    def test_empty_detections(self):
        """Test reading order with empty list."""
        result = assign_reading_order([])
        assert result == []

    def test_top_to_bottom_order(self):
        """Test top-to-bottom reading order."""
        detections = [
            Detection(
                bbox=[10.0, 50.0, 100.0, 50.0],  # y=50 (middle)
                confidence=0.9,
                class_id=9,
                class_label=ClassLabelEnum.TEXT,
            ),
            Detection(
                bbox=[10.0, 10.0, 100.0, 50.0],  # y=10 (top)
                confidence=0.8,
                class_id=10,
                class_label=ClassLabelEnum.TITLE,
            ),
            Detection(
                bbox=[10.0, 150.0, 100.0, 50.0],  # y=150 (bottom)
                confidence=0.7,
                class_id=9,
                class_label=ClassLabelEnum.TEXT,
            ),
        ]

        result = assign_reading_order(detections, method="top_to_bottom")

        # Should be sorted by y-coordinate
        assert result[0].bbox[1] == 10.0  # Top
        assert result[1].bbox[1] == 50.0  # Middle
        assert result[2].bbox[1] == 150.0  # Bottom

    def test_left_to_right_order(self):
        """Test left-to-right reading order."""
        detections = [
            Detection(
                bbox=[50.0, 10.0, 100.0, 50.0],  # x=50 (middle)
                confidence=0.9,
                class_id=9,
                class_label=ClassLabelEnum.TEXT,
            ),
            Detection(
                bbox=[10.0, 10.0, 100.0, 50.0],  # x=10 (left)
                confidence=0.8,
                class_id=10,
                class_label=ClassLabelEnum.TITLE,
            ),
            Detection(
                bbox=[150.0, 10.0, 100.0, 50.0],  # x=150 (right)
                confidence=0.7,
                class_id=9,
                class_label=ClassLabelEnum.TEXT,
            ),
        ]

        result = assign_reading_order(detections, method="left_to_right")

        # Should be sorted by x-coordinate
        assert result[0].bbox[0] == 10.0  # Left
        assert result[1].bbox[0] == 50.0  # Middle
        assert result[2].bbox[0] == 150.0  # Right

    def test_natural_reading_order(self):
        """Test natural reading order (top-to-bottom, then left-to-right)."""
        detections = [
            Detection(
                bbox=[150.0, 10.0, 100.0, 50.0],  # Top-right
                confidence=0.9,
                class_id=9,
                class_label=ClassLabelEnum.TEXT,
            ),
            Detection(
                bbox=[10.0, 10.0, 100.0, 50.0],  # Top-left
                confidence=0.8,
                class_id=10,
                class_label=ClassLabelEnum.TITLE,
            ),
            Detection(
                bbox=[10.0, 100.0, 100.0, 50.0],  # Bottom-left
                confidence=0.7,
                class_id=9,
                class_label=ClassLabelEnum.TEXT,
            ),
        ]

        result = assign_reading_order(detections, method="natural")

        # Should be sorted by (y, x)
        assert result[0].bbox == [10.0, 10.0, 100.0, 50.0]  # Top-left
        assert result[1].bbox == [150.0, 10.0, 100.0, 50.0]  # Top-right
        assert result[2].bbox == [10.0, 100.0, 100.0, 50.0]  # Bottom-left

    def test_invalid_method_raises_error(self):
        """Test invalid reading order method raises ValueError."""
        det = Detection(
            bbox=[10.0, 10.0, 100.0, 100.0],
            confidence=0.9,
            class_id=9,
            class_label=ClassLabelEnum.TEXT,
        )

        with pytest.raises(ValueError, match="Unknown reading order method"):
            assign_reading_order([det], method="invalid_method")


class TestRemoveOverlappingClasses:
    """Test class priority-based overlap removal."""

    def test_empty_detections(self):
        """Test with empty detection list."""
        result = remove_overlapping_classes([])
        assert result == []

    def test_no_overlap_keeps_all(self):
        """Test keeps all detections when no overlap."""
        detections = [
            Detection(
                bbox=[0.0, 0.0, 50.0, 50.0],
                confidence=0.9,
                class_id=10,
                class_label=ClassLabelEnum.TITLE,
            ),
            Detection(
                bbox=[100.0, 100.0, 50.0, 50.0],
                confidence=0.8,
                class_id=9,
                class_label=ClassLabelEnum.TEXT,
            ),
        ]

        result = remove_overlapping_classes(detections, iou_threshold=0.7)
        assert len(result) == 2

    def test_title_has_priority_over_text(self):
        """Test title has higher priority than text when overlapping."""
        detections = [
            Detection(
                bbox=[10.0, 10.0, 100.0, 50.0],
                confidence=0.9,
                class_id=10,  # title (priority 1)
                class_label=ClassLabelEnum.TITLE,
            ),
            Detection(
                bbox=[15.0, 15.0, 100.0, 50.0],  # High overlap
                confidence=0.8,
                class_id=9,  # text (priority 8)
                class_label=ClassLabelEnum.TEXT,
            ),
        ]

        result = remove_overlapping_classes(detections, iou_threshold=0.7)

        # Should keep title (higher priority)
        assert len(result) == 1
        assert result[0].class_label == ClassLabelEnum.TITLE

    def test_custom_priority(self):
        """Test with custom class priorities."""
        detections = [
            Detection(
                bbox=[10.0, 10.0, 100.0, 50.0],
                confidence=0.9,
                class_id=9,  # text
                class_label=ClassLabelEnum.TEXT,
            ),
            Detection(
                bbox=[15.0, 15.0, 100.0, 50.0],
                confidence=0.8,
                class_id=10,  # title
                class_label=ClassLabelEnum.TITLE,
            ),
        ]

        # Custom priority: text > title (reverse of default)
        custom_priority = {9: 1, 10: 2}  # text has higher priority

        result = remove_overlapping_classes(
            detections, class_priority=custom_priority, iou_threshold=0.7
        )

        # Should keep text (higher priority in custom mapping)
        assert len(result) == 1
        assert result[0].class_label == ClassLabelEnum.TEXT

    def test_iou_threshold_behavior(self):
        """Test IoU threshold behavior for overlap removal."""
        detections = [
            Detection(
                bbox=[10.0, 10.0, 100.0, 50.0],
                confidence=0.9,
                class_id=10,
                class_label=ClassLabelEnum.TITLE,
            ),
            Detection(
                bbox=[50.0, 50.0, 100.0, 50.0],  # Partial overlap (~6.4% IoU)
                confidence=0.8,
                class_id=9,
                class_label=ClassLabelEnum.TEXT,
            ),
        ]

        # High threshold (0.9): requires very high overlap to suppress
        # Since IoU (~0.064) < 0.9, no suppression occurs
        result = remove_overlapping_classes(detections, iou_threshold=0.9)
        assert len(result) == 2  # Both kept (overlap not high enough)

        # Low threshold (0.01): suppresses even with low overlap
        # Since IoU (~0.064) > 0.01, suppression occurs
        result = remove_overlapping_classes(detections, iou_threshold=0.01)
        assert len(result) == 1  # Only title kept (higher priority)
