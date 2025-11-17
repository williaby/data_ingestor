"""
Evaluation metrics for layout detection.

Implements standard object detection metrics:
- mAP (mean Average Precision) at IoU thresholds
- Per-class precision, recall, F1 scores
- Confusion matrix for class predictions

These metrics follow the COCO evaluation protocol commonly used for
layout detection benchmarks (DocLayNet, PubLayNet, etc.).
"""

from typing import Optional

import numpy as np

from project_b.layout.detector import Detection
from project_b.layout.postprocessing import compute_iou


def compute_precision_recall_f1(
    true_positives: int,
    false_positives: int,
    false_negatives: int,
) -> tuple[float, float, float]:
    """
    Compute precision, recall, and F1 score from TP/FP/FN counts.

    Args:
        true_positives: Number of correct predictions
        false_positives: Number of incorrect predictions
        false_negatives: Number of missed ground truths

    Returns:
        Tuple of (precision, recall, f1_score)
        Returns 0.0 for undefined values (division by zero)

    **Example:**
        ```python
        precision, recall, f1 = compute_precision_recall_f1(tp=85, fp=15, fn=10)
        print(f"Precision: {precision:.2%}, Recall: {recall:.2%}, F1: {f1:.3f}")
        ```
    """
    # Precision = TP / (TP + FP)
    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives) > 0
        else 0.0
    )

    # Recall = TP / (TP + FN)
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives) > 0
        else 0.0
    )

    # F1 = 2 * (Precision * Recall) / (Precision + Recall)
    f1_score = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return precision, recall, f1_score


def match_detections_to_ground_truth(
    predictions: list[Detection],
    ground_truths: list[Detection],
    iou_threshold: float = 0.5,
) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    """
    Match predicted detections to ground truth boxes using IoU threshold.

    This implements the standard COCO matching algorithm:
    1. Compute IoU between all prediction-GT pairs
    2. Sort by IoU (descending)
    3. Greedily match predictions to GTs (each GT matched at most once)

    Args:
        predictions: List of predicted Detection objects
        ground_truths: List of ground truth Detection objects
        iou_threshold: Minimum IoU to consider a match (default: 0.5)

    Returns:
        Tuple of (matches, unmatched_preds, unmatched_gts):
        - matches: List of (pred_idx, gt_idx) pairs
        - unmatched_preds: List of prediction indices with no match
        - unmatched_gts: List of ground truth indices with no match

    **Example:**
        ```python
        matches, fp_indices, fn_indices = match_detections_to_ground_truth(
            predictions=pred_boxes,
            ground_truths=gt_boxes,
            iou_threshold=0.5
        )
        print(f"Matched: {len(matches)}, FP: {len(fp_indices)}, FN: {len(fn_indices)}")
        ```
    """
    if not predictions or not ground_truths:
        # No matches possible
        unmatched_preds = list(range(len(predictions)))
        unmatched_gts = list(range(len(ground_truths)))
        return [], unmatched_preds, unmatched_gts

    # Compute IoU matrix (predictions x ground_truths)
    iou_matrix = np.zeros((len(predictions), len(ground_truths)))

    for i, pred in enumerate(predictions):
        for j, gt in enumerate(ground_truths):
            # Only compute IoU if classes match
            if pred.class_id == gt.class_id:
                iou_matrix[i, j] = compute_iou(pred.bbox, gt.bbox)

    # Find all potential matches above threshold
    potential_matches = []
    for i in range(len(predictions)):
        for j in range(len(ground_truths)):
            if iou_matrix[i, j] >= iou_threshold:
                potential_matches.append((i, j, iou_matrix[i, j]))

    # Sort by IoU (descending) for greedy matching
    potential_matches.sort(key=lambda x: x[2], reverse=True)

    # Greedy matching (each GT matched at most once)
    matched_preds = set()
    matched_gts = set()
    matches = []

    for pred_idx, gt_idx, iou_val in potential_matches:
        if pred_idx not in matched_preds and gt_idx not in matched_gts:
            matches.append((pred_idx, gt_idx))
            matched_preds.add(pred_idx)
            matched_gts.add(gt_idx)

    # Find unmatched predictions and ground truths
    unmatched_preds = [i for i in range(len(predictions)) if i not in matched_preds]
    unmatched_gts = [j for j in range(len(ground_truths)) if j not in matched_gts]

    return matches, unmatched_preds, unmatched_gts


def compute_average_precision(
    predictions: list[Detection],
    ground_truths: list[Detection],
    iou_threshold: float = 0.5,
) -> float:
    """
    Compute Average Precision (AP) for a single class at a given IoU threshold.

    AP is computed using the COCO protocol:
    1. Sort predictions by confidence (descending)
    2. Match predictions to ground truths
    3. Compute precision at each recall level
    4. AP = area under precision-recall curve (using 101-point interpolation)

    Args:
        predictions: List of predicted Detection objects (single class)
        ground_truths: List of ground truth Detection objects (single class)
        iou_threshold: IoU threshold for matching (default: 0.5)

    Returns:
        Average Precision (AP) value in [0.0, 1.0]
        Returns 0.0 if no ground truths or predictions

    **Example:**
        ```python
        # Filter to single class
        pred_text = [d for d in predictions if d.class_label == ClassLabelEnum.TEXT]
        gt_text = [d for d in ground_truths if d.class_label == ClassLabelEnum.TEXT]

        ap = compute_average_precision(pred_text, gt_text, iou_threshold=0.5)
        print(f"AP@0.50 for 'text' class: {ap:.3f}")
        ```
    """
    if not ground_truths:
        # No ground truth boxes - AP is undefined, return 0
        return 0.0

    if not predictions:
        # No predictions but have ground truths - AP is 0
        return 0.0

    # Sort predictions by confidence (descending)
    sorted_preds = sorted(predictions, key=lambda d: d.confidence, reverse=True)

    # Track which GTs have been matched
    gt_matched = np.zeros(len(ground_truths), dtype=bool)

    # Track TP/FP for each prediction
    tp = np.zeros(len(sorted_preds))
    fp = np.zeros(len(sorted_preds))

    for i, pred in enumerate(sorted_preds):
        # Find best matching GT
        best_iou = 0.0
        best_gt_idx = -1

        for j, gt in enumerate(ground_truths):
            # Only match same class
            if pred.class_id != gt.class_id:
                continue

            iou = compute_iou(pred.bbox, gt.bbox)
            if iou > best_iou:
                best_iou = iou
                best_gt_idx = j

        # Determine if TP or FP
        if best_iou >= iou_threshold and not gt_matched[best_gt_idx]:
            # True positive: matched to unmatched GT
            tp[i] = 1
            gt_matched[best_gt_idx] = True
        else:
            # False positive: no match or GT already matched
            fp[i] = 1

    # Compute cumulative TP and FP
    tp_cumsum = np.cumsum(tp)
    fp_cumsum = np.cumsum(fp)

    # Compute precision and recall at each threshold
    recalls = tp_cumsum / len(ground_truths)
    precisions = tp_cumsum / (tp_cumsum + fp_cumsum)

    # Add sentinel values at beginning
    recalls = np.concatenate([[0], recalls])
    precisions = np.concatenate([[1], precisions])

    # Compute AP using 101-point interpolation (COCO style)
    ap = 0.0
    recall_thresholds = np.linspace(0, 1, 101)

    for recall_t in recall_thresholds:
        # Find precisions at recall >= recall_t
        precs_at_recall = precisions[recalls >= recall_t]
        if len(precs_at_recall) > 0:
            # Maximum precision at this recall level
            ap += precs_at_recall.max()

    # Average over 101 points
    ap = ap / 101.0

    return ap


def compute_map(
    predictions: list[Detection],
    ground_truths: list[Detection],
    iou_threshold: float = 0.5,
    class_ids: Optional[list[int]] = None,
) -> dict[str, float]:
    """
    Compute mean Average Precision (mAP) across classes.

    mAP is the mean of AP values across all classes. This is the primary
    metric for object detection evaluation.

    Args:
        predictions: List of all predicted Detection objects
        ground_truths: List of all ground truth Detection objects
        iou_threshold: IoU threshold for matching (default: 0.5)
        class_ids: List of class IDs to evaluate. If None, uses all classes
                   present in ground truths.

    Returns:
        Dictionary with:
        - "mAP": mean Average Precision across all classes
        - "AP_class_{id}": AP for each individual class

    **Example:**
        ```python
        results = compute_map(
            predictions=all_predictions,
            ground_truths=all_ground_truths,
            iou_threshold=0.5
        )
        print(f"mAP@0.50: {results['mAP']:.3f}")
        for class_id in range(11):
            print(f"  Class {class_id} AP: {results[f'AP_class_{class_id}']:.3f}")
        ```
    """
    # Determine which classes to evaluate
    if class_ids is None:
        # Use all classes present in ground truths
        class_ids = sorted(set(gt.class_id for gt in ground_truths))

    if not class_ids:
        return {"mAP": 0.0}

    # Compute AP for each class
    ap_values = []
    results = {}

    for class_id in class_ids:
        # Filter predictions and GTs for this class
        class_preds = [d for d in predictions if d.class_id == class_id]
        class_gts = [d for d in ground_truths if d.class_id == class_id]

        # Compute AP
        ap = compute_average_precision(class_preds, class_gts, iou_threshold)

        ap_values.append(ap)
        results[f"AP_class_{class_id}"] = ap

    # Compute mAP (mean across classes)
    results["mAP"] = float(np.mean(ap_values)) if ap_values else 0.0

    return results


def compute_confusion_matrix(
    predictions: list[Detection],
    ground_truths: list[Detection],
    num_classes: int,
    iou_threshold: float = 0.5,
) -> np.ndarray:
    """
    Compute confusion matrix for predicted vs ground truth classes.

    The confusion matrix shows how often each predicted class matches
    each ground truth class. Element [i, j] = count of GT class i
    predicted as class j.

    Args:
        predictions: List of predicted Detection objects
        ground_truths: List of ground truth Detection objects
        num_classes: Total number of classes (e.g., 11 for DocLayNet)
        iou_threshold: IoU threshold for matching boxes

    Returns:
        Confusion matrix of shape (num_classes, num_classes)
        Rows = ground truth classes, Columns = predicted classes

    **Example:**
        ```python
        cm = compute_confusion_matrix(predictions, ground_truths, num_classes=11)

        # Diagonal elements = correct classifications
        correct = np.diag(cm).sum()
        total = cm.sum()
        accuracy = correct / total if total > 0 else 0
        print(f"Overall accuracy: {accuracy:.2%}")
        ```
    """
    confusion = np.zeros((num_classes, num_classes), dtype=int)

    if not predictions or not ground_truths:
        return confusion

    # Match predictions to ground truths
    matches, _, _ = match_detections_to_ground_truth(
        predictions, ground_truths, iou_threshold
    )

    # Fill confusion matrix for matched pairs
    for pred_idx, gt_idx in matches:
        pred_class = predictions[pred_idx].class_id
        gt_class = ground_truths[gt_idx].class_id

        confusion[gt_class, pred_class] += 1

    return confusion


def compute_per_class_metrics(
    predictions: list[Detection],
    ground_truths: list[Detection],
    iou_threshold: float = 0.5,
    class_ids: Optional[list[int]] = None,
) -> dict[int, dict[str, float]]:
    """
    Compute precision, recall, and F1 for each class.

    Args:
        predictions: List of predicted Detection objects
        ground_truths: List of ground truth Detection objects
        iou_threshold: IoU threshold for matching
        class_ids: List of class IDs to evaluate. If None, uses all classes.

    Returns:
        Dictionary mapping class_id -> {"precision": float, "recall": float, "f1": float}

    **Example:**
        ```python
        metrics = compute_per_class_metrics(predictions, ground_truths)

        for class_id, scores in metrics.items():
            print(f"Class {class_id}: "
                  f"P={scores['precision']:.2%}, "
                  f"R={scores['recall']:.2%}, "
                  f"F1={scores['f1']:.3f}")
        ```
    """
    # Determine which classes to evaluate
    if class_ids is None:
        class_ids = sorted(
            set(d.class_id for d in predictions + ground_truths)
        )

    results = {}

    for class_id in class_ids:
        # Filter to this class
        class_preds = [d for d in predictions if d.class_id == class_id]
        class_gts = [d for d in ground_truths if d.class_id == class_id]

        # Match detections
        matches, fp_indices, fn_indices = match_detections_to_ground_truth(
            class_preds, class_gts, iou_threshold
        )

        # Compute TP/FP/FN
        tp = len(matches)
        fp = len(fp_indices)
        fn = len(fn_indices)

        # Compute metrics
        precision, recall, f1 = compute_precision_recall_f1(tp, fp, fn)

        results[class_id] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }

    return results
