"""
Layout detection metrics.

Implements metrics for evaluating layout detection quality:
- mAP (mean Average Precision): Layout class detection across document
"""


def calculate_map(
    predicted_boxes: list[dict],
    ground_truth_boxes: list[dict],
    iou_threshold: float = 0.5,
) -> float:
    """
    Calculate mAP (mean Average Precision) for layout detection.

    mAP measures how well layout elements are detected across multiple classes.
    Uses IoU (Intersection over Union) for bounding box matching.

    Args:
        predicted_boxes: List of predicted boxes with class, bbox coordinates
        ground_truth_boxes: List of ground truth boxes
        iou_threshold: IoU threshold for considering a match (default: 0.5)

    Returns:
        mAP score (0.0-1.0, higher = better)

    # TODO(Phase 1.5): Implement proper mAP calculation with per-class AP
    # TODO(Phase 1.5): Use COCO-style mAP with multiple IoU thresholds
    # TODO(Phase 1.5): Handle confidence scores for ranking predictions
    """
    if not ground_truth_boxes:
        return 1.0 if not predicted_boxes else 0.0

    if not predicted_boxes:
        return 0.0

    # Get unique classes
    classes = set(box.get("class") for box in ground_truth_boxes)

    # Calculate AP for each class
    aps = []
    for cls in classes:
        ap = _calculate_class_ap(
            predicted_boxes,
            ground_truth_boxes,
            cls,
            iou_threshold,
        )
        aps.append(ap)

    # Mean AP across all classes
    map_score = sum(aps) / len(aps) if aps else 0.0
    return map_score


def _calculate_class_ap(
    predicted: list[dict],
    ground_truth: list[dict],
    target_class: str,
    iou_threshold: float,
) -> float:
    """Calculate Average Precision for a single class."""
    # Filter by class
    pred_cls = [p for p in predicted if p.get("class") == target_class]
    gt_cls = [g for g in ground_truth if g.get("class") == target_class]

    if not gt_cls:
        return 1.0 if not pred_cls else 0.0

    if not pred_cls:
        return 0.0

    # Match predictions to ground truth
    matched_gt = set()
    tp = 0
    fp = 0

    for pred in pred_cls:
        best_iou = 0.0
        best_gt_idx = None

        for i, gt in enumerate(gt_cls):
            if i in matched_gt:
                continue

            iou = _calculate_iou(pred.get("bbox", []), gt.get("bbox", []))
            if iou > best_iou:
                best_iou = iou
                best_gt_idx = i

        if best_iou >= iou_threshold and best_gt_idx is not None:
            tp += 1
            matched_gt.add(best_gt_idx)
        else:
            fp += 1

    fn = len(gt_cls) - tp

    # Calculate precision and recall
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    # Simplified AP (not interpolated)
    # Phase 1.5 will use proper interpolated precision-recall curve
    if precision + recall == 0:
        return 0.0

    ap = 2 * precision * recall / (precision + recall)  # F1 as simplified AP
    return ap


def _calculate_iou(bbox1: list[float], bbox2: list[float]) -> float:
    """
    Calculate Intersection over Union (IoU) for two bounding boxes.

    Args:
        bbox1: [x1, y1, x2, y2] coordinates
        bbox2: [x1, y1, x2, y2] coordinates

    Returns:
        IoU score (0.0-1.0)
    """
    if len(bbox1) != 4 or len(bbox2) != 4:
        return 0.0

    # Extract coordinates
    x1_1, y1_1, x2_1, y2_1 = bbox1
    x1_2, y1_2, x2_2, y2_2 = bbox2

    # Calculate intersection
    x1_inter = max(x1_1, x1_2)
    y1_inter = max(y1_1, y1_2)
    x2_inter = min(x2_1, x2_2)
    y2_inter = min(y2_1, y2_2)

    if x2_inter < x1_inter or y2_inter < y1_inter:
        return 0.0

    intersection = (x2_inter - x1_inter) * (y2_inter - y1_inter)

    # Calculate union
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
    union = area1 + area2 - intersection

    if union == 0:
        return 0.0

    iou = intersection / union
    return iou
