"""
Unit tests for evaluation metrics.

Tests mAP, AP, precision/recall/F1, confusion matrix, and detection matching.
"""

import numpy as np
import pytest

from project_b.layout.detector import ClassLabelEnum, Detection
from project_b.evaluation.metrics import (
    compute_average_precision,
    compute_confusion_matrix,
    compute_map,
    compute_per_class_metrics,
    compute_precision_recall_f1,
    match_detections_to_ground_truth,
)


class TestPrecisionRecallF1:
    """Test precision, recall, and F1 score computation."""

    def test_perfect_predictions(self):
        """Test metrics when all predictions are correct."""
        precision, recall, f1 = compute_precision_recall_f1(tp=10, fp=0, fn=0)

        assert precision == 1.0
        assert recall == 1.0
        assert f1 == 1.0

    def test_no_true_positives(self):
        """Test metrics when there are no true positives."""
        precision, recall, f1 = compute_precision_recall_f1(tp=0, fp=5, fn=10)

        assert precision == 0.0
        assert recall == 0.0
        assert f1 == 0.0

    def test_some_false_positives(self):
        """Test metrics with some false positives."""
        precision, recall, f1 = compute_precision_recall_f1(tp=8, fp=2, fn=0)

        assert precision == 0.8  # 8 / (8 + 2)
        assert recall == 1.0     # 8 / (8 + 0)
        assert f1 == pytest.approx(0.888, abs=0.01)  # 2 * (0.8 * 1.0) / (0.8 + 1.0)

    def test_some_false_negatives(self):
        """Test metrics with some false negatives."""
        precision, recall, f1 = compute_precision_recall_f1(tp=8, fp=0, fn=2)

        assert precision == 1.0   # 8 / (8 + 0)
        assert recall == 0.8      # 8 / (8 + 2)
        assert f1 == pytest.approx(0.888, abs=0.01)  # 2 * (1.0 * 0.8) / (1.0 + 0.8)

    def test_balanced_errors(self):
        """Test metrics with balanced FP and FN."""
        precision, recall, f1 = compute_precision_recall_f1(tp=6, fp=2, fn=2)

        assert precision == 0.75  # 6 / (6 + 2)
        assert recall == 0.75     # 6 / (6 + 2)
        assert f1 == 0.75         # 2 * (0.75 * 0.75) / (0.75 + 0.75)


class TestDetectionMatching:
    """Test greedy detection-to-GT matching algorithm."""

    def test_perfect_match_single_detection(self):
        """Test perfect 1:1 match between detection and GT."""
        pred = Detection(
            bbox=[10.0, 10.0, 100.0, 100.0],
            confidence=0.9,
            class_id=9,
            class_label=ClassLabelEnum.TEXT,
        )
        gt = Detection(
            bbox=[10.0, 10.0, 100.0, 100.0],  # Perfect overlap
            confidence=1.0,
            class_id=9,
            class_label=ClassLabelEnum.TEXT,
        )

        matches, unmatched_preds, unmatched_gts = match_detections_to_ground_truth(
            [pred], [gt], iou_threshold=0.5
        )

        assert len(matches) == 1
        assert matches[0] == (0, 0)  # Pred 0 matched to GT 0
        assert len(unmatched_preds) == 0
        assert len(unmatched_gts) == 0

    def test_no_overlap_no_match(self):
        """Test that non-overlapping boxes don't match."""
        pred = Detection(
            bbox=[10.0, 10.0, 50.0, 50.0],
            confidence=0.9,
            class_id=9,
            class_label=ClassLabelEnum.TEXT,
        )
        gt = Detection(
            bbox=[200.0, 200.0, 50.0, 50.0],  # No overlap
            confidence=1.0,
            class_id=9,
            class_label=ClassLabelEnum.TEXT,
        )

        matches, unmatched_preds, unmatched_gts = match_detections_to_ground_truth(
            [pred], [gt], iou_threshold=0.5
        )

        assert len(matches) == 0
        assert unmatched_preds == [0]
        assert unmatched_gts == [0]

    def test_class_mismatch_no_match(self):
        """Test that different classes don't match even with high IoU."""
        pred = Detection(
            bbox=[10.0, 10.0, 100.0, 100.0],
            confidence=0.9,
            class_id=9,  # text
            class_label=ClassLabelEnum.TEXT,
        )
        gt = Detection(
            bbox=[10.0, 10.0, 100.0, 100.0],  # Perfect overlap
            confidence=1.0,
            class_id=10,  # title (different class)
            class_label=ClassLabelEnum.TITLE,
        )

        matches, unmatched_preds, unmatched_gts = match_detections_to_ground_truth(
            [pred], [gt], iou_threshold=0.5
        )

        assert len(matches) == 0
        assert unmatched_preds == [0]
        assert unmatched_gts == [0]

    def test_multiple_predictions_greedy_matching(self):
        """Test greedy matching with multiple predictions."""
        # Two predictions overlapping same GT
        pred1 = Detection(
            bbox=[10.0, 10.0, 100.0, 100.0],
            confidence=0.9,
            class_id=9,
            class_label=ClassLabelEnum.TEXT,
        )
        pred2 = Detection(
            bbox=[15.0, 15.0, 100.0, 100.0],  # Slightly offset
            confidence=0.8,
            class_id=9,
            class_label=ClassLabelEnum.TEXT,
        )
        gt = Detection(
            bbox=[10.0, 10.0, 100.0, 100.0],
            confidence=1.0,
            class_id=9,
            class_label=ClassLabelEnum.TEXT,
        )

        matches, unmatched_preds, unmatched_gts = match_detections_to_ground_truth(
            [pred1, pred2], [gt], iou_threshold=0.5
        )

        # Only pred1 should match (higher IoU due to perfect alignment)
        assert len(matches) == 1
        assert matches[0] == (0, 0)  # Pred1 matched to GT
        assert 1 in unmatched_preds  # Pred2 unmatched
        assert len(unmatched_gts) == 0

    def test_empty_predictions(self):
        """Test matching with no predictions."""
        gt = Detection(
            bbox=[10.0, 10.0, 100.0, 100.0],
            confidence=1.0,
            class_id=9,
            class_label=ClassLabelEnum.TEXT,
        )

        matches, unmatched_preds, unmatched_gts = match_detections_to_ground_truth(
            [], [gt], iou_threshold=0.5
        )

        assert len(matches) == 0
        assert len(unmatched_preds) == 0
        assert unmatched_gts == [0]

    def test_empty_ground_truths(self):
        """Test matching with no ground truths."""
        pred = Detection(
            bbox=[10.0, 10.0, 100.0, 100.0],
            confidence=0.9,
            class_id=9,
            class_label=ClassLabelEnum.TEXT,
        )

        matches, unmatched_preds, unmatched_gts = match_detections_to_ground_truth(
            [pred], [], iou_threshold=0.5
        )

        assert len(matches) == 0
        assert unmatched_preds == [0]
        assert len(unmatched_gts) == 0


class TestAveragePrecision:
    """Test Average Precision computation."""

    def test_perfect_predictions(self):
        """Test AP when all predictions are correct and confident."""
        # 3 ground truths, 3 correct predictions
        predictions = [
            Detection(bbox=[10.0, 10.0, 50.0, 50.0], confidence=0.9,
                     class_id=9, class_label=ClassLabelEnum.TEXT),
            Detection(bbox=[100.0, 100.0, 50.0, 50.0], confidence=0.85,
                     class_id=9, class_label=ClassLabelEnum.TEXT),
            Detection(bbox=[200.0, 200.0, 50.0, 50.0], confidence=0.8,
                     class_id=9, class_label=ClassLabelEnum.TEXT),
        ]
        ground_truths = [
            Detection(bbox=[10.0, 10.0, 50.0, 50.0], confidence=1.0,
                     class_id=9, class_label=ClassLabelEnum.TEXT),
            Detection(bbox=[100.0, 100.0, 50.0, 50.0], confidence=1.0,
                     class_id=9, class_label=ClassLabelEnum.TEXT),
            Detection(bbox=[200.0, 200.0, 50.0, 50.0], confidence=1.0,
                     class_id=9, class_label=ClassLabelEnum.TEXT),
        ]

        ap = compute_average_precision(predictions, ground_truths, iou_threshold=0.5)

        # Perfect predictions should give AP = 1.0
        assert ap == pytest.approx(1.0, abs=0.01)

    def test_no_predictions(self):
        """Test AP when there are no predictions."""
        ground_truths = [
            Detection(bbox=[10.0, 10.0, 50.0, 50.0], confidence=1.0,
                     class_id=9, class_label=ClassLabelEnum.TEXT),
        ]

        ap = compute_average_precision([], ground_truths, iou_threshold=0.5)

        # No predictions should give AP = 0.0
        assert ap == 0.0

    def test_no_ground_truths(self):
        """Test AP when there are no ground truths."""
        predictions = [
            Detection(bbox=[10.0, 10.0, 50.0, 50.0], confidence=0.9,
                     class_id=9, class_label=ClassLabelEnum.TEXT),
        ]

        ap = compute_average_precision(predictions, [], iou_threshold=0.5)

        # No GTs should give AP = 0.0
        assert ap == 0.0

    def test_partial_matches(self):
        """Test AP with some correct and some incorrect predictions."""
        # 2 GTs, 3 predictions (1 TP, 1 FP, 1 TP)
        predictions = [
            Detection(bbox=[10.0, 10.0, 50.0, 50.0], confidence=0.9,
                     class_id=9, class_label=ClassLabelEnum.TEXT),  # TP
            Detection(bbox=[300.0, 300.0, 50.0, 50.0], confidence=0.85,
                     class_id=9, class_label=ClassLabelEnum.TEXT),  # FP (no match)
            Detection(bbox=[100.0, 100.0, 50.0, 50.0], confidence=0.8,
                     class_id=9, class_label=ClassLabelEnum.TEXT),  # TP
        ]
        ground_truths = [
            Detection(bbox=[10.0, 10.0, 50.0, 50.0], confidence=1.0,
                     class_id=9, class_label=ClassLabelEnum.TEXT),
            Detection(bbox=[100.0, 100.0, 50.0, 50.0], confidence=1.0,
                     class_id=9, class_label=ClassLabelEnum.TEXT),
        ]

        ap = compute_average_precision(predictions, ground_truths, iou_threshold=0.5)

        # AP should be > 0 but < 1.0 due to FP
        assert 0.0 < ap < 1.0


class TestMeanAveragePrecision:
    """Test mAP computation across multiple classes."""

    def test_single_class_perfect(self):
        """Test mAP with single class and perfect predictions."""
        predictions = [
            Detection(bbox=[10.0, 10.0, 50.0, 50.0], confidence=0.9,
                     class_id=9, class_label=ClassLabelEnum.TEXT),
        ]
        ground_truths = [
            Detection(bbox=[10.0, 10.0, 50.0, 50.0], confidence=1.0,
                     class_id=9, class_label=ClassLabelEnum.TEXT),
        ]

        results = compute_map(predictions, ground_truths, iou_threshold=0.5)

        assert "mAP" in results
        assert results["mAP"] == pytest.approx(1.0, abs=0.01)
        assert 9 in results["per_class_AP"]
        assert results["per_class_AP"][9] == pytest.approx(1.0, abs=0.01)

    def test_multiple_classes(self):
        """Test mAP with multiple classes."""
        predictions = [
            # Class 9 (text): 1 correct prediction
            Detection(bbox=[10.0, 10.0, 50.0, 50.0], confidence=0.9,
                     class_id=9, class_label=ClassLabelEnum.TEXT),
            # Class 10 (title): 1 correct prediction
            Detection(bbox=[100.0, 100.0, 50.0, 50.0], confidence=0.85,
                     class_id=10, class_label=ClassLabelEnum.TITLE),
        ]
        ground_truths = [
            Detection(bbox=[10.0, 10.0, 50.0, 50.0], confidence=1.0,
                     class_id=9, class_label=ClassLabelEnum.TEXT),
            Detection(bbox=[100.0, 100.0, 50.0, 50.0], confidence=1.0,
                     class_id=10, class_label=ClassLabelEnum.TITLE),
        ]

        results = compute_map(predictions, ground_truths, iou_threshold=0.5)

        assert "mAP" in results
        # mAP should be average of per-class APs (both should be 1.0)
        assert results["mAP"] == pytest.approx(1.0, abs=0.01)
        assert 9 in results["per_class_AP"]
        assert 10 in results["per_class_AP"]

    def test_no_predictions_all_classes(self):
        """Test mAP when there are no predictions."""
        ground_truths = [
            Detection(bbox=[10.0, 10.0, 50.0, 50.0], confidence=1.0,
                     class_id=9, class_label=ClassLabelEnum.TEXT),
        ]

        results = compute_map([], ground_truths, iou_threshold=0.5)

        assert results["mAP"] == 0.0


class TestPerClassMetrics:
    """Test per-class precision/recall/F1 computation."""

    def test_single_class_perfect(self):
        """Test per-class metrics with perfect predictions for one class."""
        predictions = [
            Detection(bbox=[10.0, 10.0, 50.0, 50.0], confidence=0.9,
                     class_id=9, class_label=ClassLabelEnum.TEXT),
        ]
        ground_truths = [
            Detection(bbox=[10.0, 10.0, 50.0, 50.0], confidence=1.0,
                     class_id=9, class_label=ClassLabelEnum.TEXT),
        ]

        metrics = compute_per_class_metrics(
            predictions, ground_truths, num_classes=11, iou_threshold=0.5
        )

        assert 9 in metrics
        assert metrics[9]["precision"] == 1.0
        assert metrics[9]["recall"] == 1.0
        assert metrics[9]["f1"] == 1.0
        assert metrics[9]["tp"] == 1
        assert metrics[9]["fp"] == 0
        assert metrics[9]["fn"] == 0

    def test_multiple_classes_with_errors(self):
        """Test per-class metrics with multiple classes and errors."""
        predictions = [
            # Class 9: 1 TP
            Detection(bbox=[10.0, 10.0, 50.0, 50.0], confidence=0.9,
                     class_id=9, class_label=ClassLabelEnum.TEXT),
            # Class 9: 1 FP (no GT match)
            Detection(bbox=[300.0, 300.0, 50.0, 50.0], confidence=0.85,
                     class_id=9, class_label=ClassLabelEnum.TEXT),
        ]
        ground_truths = [
            # Class 9: 1 GT (matched)
            Detection(bbox=[10.0, 10.0, 50.0, 50.0], confidence=1.0,
                     class_id=9, class_label=ClassLabelEnum.TEXT),
            # Class 10: 1 GT (unmatched - FN)
            Detection(bbox=[100.0, 100.0, 50.0, 50.0], confidence=1.0,
                     class_id=10, class_label=ClassLabelEnum.TITLE),
        ]

        metrics = compute_per_class_metrics(
            predictions, ground_truths, num_classes=11, iou_threshold=0.5
        )

        # Class 9: TP=1, FP=1, FN=0
        assert metrics[9]["tp"] == 1
        assert metrics[9]["fp"] == 1
        assert metrics[9]["fn"] == 0
        assert metrics[9]["precision"] == 0.5  # 1 / (1 + 1)
        assert metrics[9]["recall"] == 1.0     # 1 / (1 + 0)

        # Class 10: TP=0, FP=0, FN=1
        assert metrics[10]["tp"] == 0
        assert metrics[10]["fp"] == 0
        assert metrics[10]["fn"] == 1
        assert metrics[10]["precision"] == 0.0
        assert metrics[10]["recall"] == 0.0


class TestConfusionMatrix:
    """Test confusion matrix computation."""

    def test_perfect_predictions(self):
        """Test confusion matrix with perfect predictions."""
        predictions = [
            Detection(bbox=[10.0, 10.0, 50.0, 50.0], confidence=0.9,
                     class_id=9, class_label=ClassLabelEnum.TEXT),
            Detection(bbox=[100.0, 100.0, 50.0, 50.0], confidence=0.85,
                     class_id=10, class_label=ClassLabelEnum.TITLE),
        ]
        ground_truths = [
            Detection(bbox=[10.0, 10.0, 50.0, 50.0], confidence=1.0,
                     class_id=9, class_label=ClassLabelEnum.TEXT),
            Detection(bbox=[100.0, 100.0, 50.0, 50.0], confidence=1.0,
                     class_id=10, class_label=ClassLabelEnum.TITLE),
        ]

        cm = compute_confusion_matrix(
            predictions, ground_truths, num_classes=11, iou_threshold=0.5
        )

        # Check shape
        assert cm.shape == (11, 11)

        # Check diagonal (correct predictions)
        assert cm[9, 9] == 1  # Text correctly predicted as text
        assert cm[10, 10] == 1  # Title correctly predicted as title

        # All other entries should be 0
        for i in range(11):
            for j in range(11):
                if i == j and i in [9, 10]:
                    continue
                assert cm[i, j] == 0

    def test_misclassification(self):
        """Test confusion matrix with misclassified predictions."""
        predictions = [
            # Predict as text (class 9)
            Detection(bbox=[10.0, 10.0, 50.0, 50.0], confidence=0.9,
                     class_id=9, class_label=ClassLabelEnum.TEXT),
        ]
        ground_truths = [
            # Actually title (class 10)
            Detection(bbox=[10.0, 10.0, 50.0, 50.0], confidence=1.0,
                     class_id=10, class_label=ClassLabelEnum.TITLE),
        ]

        cm = compute_confusion_matrix(
            predictions, ground_truths, num_classes=11, iou_threshold=0.5
        )

        # Check misclassification (GT class 10 predicted as class 9)
        assert cm[10, 9] == 1  # Row = GT class, Col = Pred class

    def test_empty_predictions_empty_gts(self):
        """Test confusion matrix with no predictions and no GTs."""
        cm = compute_confusion_matrix([], [], num_classes=11, iou_threshold=0.5)

        # All zeros
        assert np.all(cm == 0)
        assert cm.shape == (11, 11)
