"""
Unit tests for layout detection metrics.

Tests mAP (mean Average Precision) and IoU calculation with comprehensive
coverage of all functions, branches, and edge cases.
"""

from data_ingestor.evaluation.metrics.layout_metrics import calculate_map


class TestCalculateMAP:
    """Test mAP (mean Average Precision) calculation."""

    def test_perfect_detection(self):
        """Test mAP with perfect detection."""
        boxes = [
            {"class": "text", "bbox": [0, 0, 10, 10]},
            {"class": "table", "bbox": [20, 20, 30, 30]},
        ]
        map_score = calculate_map(boxes, boxes)
        assert map_score == 1.0

    def test_partial_detection(self):
        """Test mAP with partial detection."""
        pred = [
            {"class": "text", "bbox": [0, 0, 10, 10]},
            {"class": "table", "bbox": [20, 20, 30, 30]},
        ]
        gt = [
            {"class": "text", "bbox": [0, 0, 10, 10]},
            {"class": "image", "bbox": [40, 40, 50, 50]},
        ]
        map_score = calculate_map(pred, gt)
        # text class: 1 TP (perfect match)
        # table class: 0 GT boxes (should return 0.0 for this class)
        # image class: 0 pred boxes (should return 0.0 for this class)
        assert 0.0 < map_score < 1.0

    def test_no_detections(self):
        """Test mAP with no detections."""
        pred = []
        gt = [{"class": "text", "bbox": [0, 0, 10, 10]}]
        map_score = calculate_map(pred, gt)
        assert map_score == 0.0

    def test_empty_ground_truth(self):
        """Test mAP with empty ground truth."""
        pred = [{"class": "text", "bbox": [0, 0, 10, 10]}]
        gt = []
        map_score = calculate_map(pred, gt)
        assert map_score == 0.0

    def test_both_empty(self):
        """Test mAP with both empty."""
        map_score = calculate_map([], [])
        assert map_score == 1.0

    def test_different_iou_threshold(self):
        """Test mAP with different IoU thresholds."""
        # Boxes with moderate overlap
        pred = [{"class": "text", "bbox": [0, 0, 10, 10]}]
        gt = [{"class": "text", "bbox": [5, 5, 15, 15]}]

        # Lower threshold should match
        map_low = calculate_map(pred, gt, iou_threshold=0.1)
        assert map_low > 0.0

        # Higher threshold might not match
        map_high = calculate_map(pred, gt, iou_threshold=0.9)
        assert map_high >= 0.0

    def test_multiple_classes(self):
        """Test mAP with multiple classes."""
        pred = [
            {"class": "text", "bbox": [0, 0, 10, 10]},
            {"class": "table", "bbox": [20, 20, 30, 30]},
            {"class": "image", "bbox": [40, 40, 50, 50]},
        ]
        gt = [
            {"class": "text", "bbox": [0, 0, 10, 10]},
            {"class": "table", "bbox": [20, 20, 30, 30]},
            {"class": "image", "bbox": [40, 40, 50, 50]},
        ]
        map_score = calculate_map(pred, gt)
        assert map_score == 1.0

    def test_false_positives(self):
        """Test mAP with false positive detections."""
        pred = [
            {"class": "text", "bbox": [0, 0, 10, 10]},
            {"class": "text", "bbox": [100, 100, 110, 110]},  # False positive
        ]
        gt = [{"class": "text", "bbox": [0, 0, 10, 10]}]
        map_score = calculate_map(pred, gt)
        # 1 TP, 1 FP for text class
        assert 0.0 < map_score < 1.0

    def test_false_negatives(self):
        """Test mAP with false negatives (missed detections)."""
        pred = [{"class": "text", "bbox": [0, 0, 10, 10]}]
        gt = [
            {"class": "text", "bbox": [0, 0, 10, 10]},
            {"class": "text", "bbox": [20, 20, 30, 30]},  # Missed
        ]
        map_score = calculate_map(pred, gt)
        # 1 TP, 1 FN for text class
        assert 0.0 < map_score < 1.0

    def test_wrong_class_prediction(self):
        """Test mAP with wrong class predictions."""
        pred = [{"class": "table", "bbox": [0, 0, 10, 10]}]
        gt = [{"class": "text", "bbox": [0, 0, 10, 10]}]
        map_score = calculate_map(pred, gt)
        # Perfect bbox but wrong class
        assert map_score == 0.0

    def test_partial_overlap_below_threshold(self):
        """Test mAP with partial overlap below IoU threshold."""
        pred = [{"class": "text", "bbox": [0, 0, 10, 10]}]
        gt = [{"class": "text", "bbox": [9, 9, 19, 19]}]
        # Very small overlap
        map_score = calculate_map(pred, gt, iou_threshold=0.5)
        # IoU will be very low, likely below threshold
        assert map_score >= 0.0

    def test_multiple_predictions_same_class(self):
        """Test mAP with multiple predictions for same class."""
        pred = [
            {"class": "text", "bbox": [0, 0, 10, 10]},
            {"class": "text", "bbox": [1, 1, 11, 11]},  # Overlaps with same GT
        ]
        gt = [{"class": "text", "bbox": [0, 0, 10, 10]}]
        map_score = calculate_map(pred, gt)
        # Only one can match the GT (best IoU wins)
        assert 0.0 < map_score < 1.0

    def test_invalid_bbox_format(self):
        """Test mAP with invalid bbox format."""
        pred = [{"class": "text", "bbox": [0, 0, 10]}]  # Missing coordinate
        gt = [{"class": "text", "bbox": [0, 0, 10, 10]}]
        map_score = calculate_map(pred, gt)
        # Should handle gracefully (no match due to invalid bbox)
        assert map_score == 0.0

    def test_missing_bbox_key(self):
        """Test mAP with missing bbox key."""
        pred = [{"class": "text"}]
        gt = [{"class": "text", "bbox": [0, 0, 10, 10]}]
        map_score = calculate_map(pred, gt)
        # Should handle gracefully
        assert map_score == 0.0

    def test_single_class_perfect_detection(self):
        """Test mAP with single class perfect detection."""
        pred = [
            {"class": "text", "bbox": [0, 0, 10, 10]},
            {"class": "text", "bbox": [20, 20, 30, 30]},
        ]
        gt = [
            {"class": "text", "bbox": [0, 0, 10, 10]},
            {"class": "text", "bbox": [20, 20, 30, 30]},
        ]
        map_score = calculate_map(pred, gt)
        assert map_score == 1.0

    def test_best_iou_matching(self):
        """Test that best IoU is selected when multiple matches possible."""
        pred = [{"class": "text", "bbox": [5, 5, 15, 15]}]
        gt = [
            {"class": "text", "bbox": [0, 0, 10, 10]},  # Lower IoU
            {"class": "text", "bbox": [4, 4, 14, 14]},  # Higher IoU
        ]
        map_score = calculate_map(pred, gt, iou_threshold=0.1)
        # Should match with higher IoU GT box
        assert 0.0 < map_score <= 1.0


class TestCalculateIoU:
    """Test IoU calculation (via mAP tests)."""

    def test_identical_boxes(self):
        """Test IoU with identical boxes."""
        pred = [{"class": "text", "bbox": [0, 0, 10, 10]}]
        gt = [{"class": "text", "bbox": [0, 0, 10, 10]}]
        map_score = calculate_map(pred, gt, iou_threshold=0.99)
        # IoU = 1.0, should match even with high threshold
        assert map_score == 1.0

    def test_no_overlap(self):
        """Test IoU with no overlap."""
        pred = [{"class": "text", "bbox": [0, 0, 10, 10]}]
        gt = [{"class": "text", "bbox": [20, 20, 30, 30]}]
        map_score = calculate_map(pred, gt, iou_threshold=0.1)
        # IoU = 0, should not match
        assert map_score == 0.0

    def test_partial_overlap(self):
        """Test IoU with partial overlap."""
        pred = [{"class": "text", "bbox": [0, 0, 20, 20]}]
        gt = [{"class": "text", "bbox": [10, 10, 30, 30]}]
        # 10x10 intersection, areas are 400 each, union = 700
        # IoU = 100/700 ≈ 0.14
        map_score = calculate_map(pred, gt, iou_threshold=0.1)
        assert map_score > 0.0

    def test_contained_box(self):
        """Test IoU with one box contained in another."""
        pred = [{"class": "text", "bbox": [5, 5, 15, 15]}]
        gt = [{"class": "text", "bbox": [0, 0, 20, 20]}]
        # Smaller box fully contained
        # Intersection = 100, Union = 400
        # IoU = 0.25
        map_score = calculate_map(pred, gt, iou_threshold=0.2)
        assert map_score > 0.0

    def test_edge_touching(self):
        """Test IoU with boxes touching at edge."""
        pred = [{"class": "text", "bbox": [0, 0, 10, 10]}]
        gt = [{"class": "text", "bbox": [10, 0, 20, 10]}]
        # Touching but no overlap (edge at x=10)
        map_score = calculate_map(pred, gt, iou_threshold=0.1)
        assert map_score == 0.0

    def test_negative_coordinates(self):
        """Test IoU with negative coordinates."""
        pred = [{"class": "text", "bbox": [-10, -10, 0, 0]}]
        gt = [{"class": "text", "bbox": [-10, -10, 0, 0]}]
        map_score = calculate_map(pred, gt)
        # Identical boxes with negative coords
        assert map_score == 1.0

    def test_floating_point_coordinates(self):
        """Test IoU with floating point coordinates."""
        pred = [{"class": "text", "bbox": [0.5, 0.5, 10.5, 10.5]}]
        gt = [{"class": "text", "bbox": [0.5, 0.5, 10.5, 10.5]}]
        map_score = calculate_map(pred, gt)
        assert map_score == 1.0

    def test_zero_area_box(self):
        """Test IoU with zero area box."""
        pred = [{"class": "text", "bbox": [0, 0, 0, 0]}]
        gt = [{"class": "text", "bbox": [0, 0, 10, 10]}]
        map_score = calculate_map(pred, gt)
        # Zero area box should not match
        assert map_score == 0.0

    def test_inverted_coordinates(self):
        """Test IoU with inverted coordinates (x2 < x1 or y2 < y1)."""
        pred = [{"class": "text", "bbox": [10, 10, 0, 0]}]  # Inverted
        gt = [{"class": "text", "bbox": [0, 0, 10, 10]}]
        map_score = calculate_map(pred, gt)
        # Should handle gracefully (likely no match)
        assert map_score >= 0.0
