"""
Postprocessing utilities for layout detection.

This module provides Non-Maximum Suppression (NMS), confidence filtering,
and bbox refinement utilities for layout detection outputs.

**Functions:**
- apply_nms: Apply Non-Maximum Suppression to remove duplicate detections
- filter_by_confidence: Filter detections by confidence threshold
- filter_by_size: Filter detections by minimum bbox size
- assign_reading_order: Assign reading order indices to detections

Schema Version: 1.0.0
"""

from typing import Optional

import numpy as np

from project_b.layout.detector import Detection


def compute_iou(bbox1: list[float], bbox2: list[float]) -> float:
    """
    Compute Intersection over Union (IoU) for two COCO format bboxes.

    Args:
        bbox1: COCO bbox [x, y, width, height]
        bbox2: COCO bbox [x, y, width, height]

    Returns:
        IoU score in [0.0, 1.0]

    **Example:**
        ```python
        bbox1 = [10.0, 10.0, 100.0, 100.0]  # x=10, y=10, w=100, h=100
        bbox2 = [50.0, 50.0, 100.0, 100.0]  # x=50, y=50, w=100, h=100
        iou = compute_iou(bbox1, bbox2)
        print(f"IoU: {iou:.2f}")  # IoU: 0.14 (partial overlap)
        ```
    """
    # Extract coordinates
    x1, y1, w1, h1 = bbox1
    x2, y2, w2, h2 = bbox2

    # Compute corners
    x1_max, y1_max = x1 + w1, y1 + h1
    x2_max, y2_max = x2 + w2, y2 + h2

    # Compute intersection area
    inter_x1 = max(x1, x2)
    inter_y1 = max(y1, y2)
    inter_x2 = min(x1_max, x2_max)
    inter_y2 = min(y1_max, y2_max)

    inter_width = max(0, inter_x2 - inter_x1)
    inter_height = max(0, inter_y2 - inter_y1)
    inter_area = inter_width * inter_height

    # Compute union area
    area1 = w1 * h1
    area2 = w2 * h2
    union_area = area1 + area2 - inter_area

    # Avoid division by zero
    if union_area == 0:
        return 0.0

    iou = inter_area / union_area
    return iou


def apply_nms(
    detections: list[Detection],
    iou_threshold: float = 0.45,
) -> list[Detection]:
    """
    Apply Non-Maximum Suppression to remove duplicate detections.

    NMS removes overlapping detections of the same class, keeping only
    the detection with highest confidence.

    Args:
        detections: List of Detection objects
        iou_threshold: IoU threshold for suppression (default: 0.45)

    Returns:
        Filtered list of detections after NMS

    **Algorithm:**
    1. Sort detections by confidence (descending)
    2. For each detection:
        - Keep if not suppressed
        - Suppress all remaining detections with IoU > threshold and same class

    **Performance:** O(N²) where N is number of detections

    **Example:**
        ```python
        from project_b.layout.postprocessing import apply_nms

        # Detections may have overlaps
        detections = detector.detect(image)
        print(f"Before NMS: {len(detections)} detections")

        # Apply NMS to remove duplicates
        filtered = apply_nms(detections, iou_threshold=0.45)
        print(f"After NMS: {len(filtered)} detections")
        ```
    """
    if not detections:
        return []

    # Sort detections by confidence (descending)
    sorted_detections = sorted(
        detections, key=lambda d: d.confidence, reverse=True
    )

    # Track which detections to keep
    keep = []
    suppressed = set()

    for i, det_i in enumerate(sorted_detections):
        if i in suppressed:
            continue

        # Keep this detection
        keep.append(det_i)

        # Suppress overlapping detections of same class
        for j, det_j in enumerate(sorted_detections[i + 1 :], start=i + 1):
            if j in suppressed:
                continue

            # Only suppress if same class
            if det_i.class_id != det_j.class_id:
                continue

            # Compute IoU
            iou = compute_iou(det_i.bbox, det_j.bbox)

            # Suppress if IoU exceeds threshold
            if iou > iou_threshold:
                suppressed.add(j)

    return keep


def filter_by_confidence(
    detections: list[Detection],
    min_confidence: float = 0.3,
) -> list[Detection]:
    """
    Filter detections by minimum confidence threshold.

    Args:
        detections: List of Detection objects
        min_confidence: Minimum confidence threshold (0.0-1.0)

    Returns:
        Filtered list of detections

    **Example:**
        ```python
        from project_b.layout.postprocessing import filter_by_confidence

        detections = detector.detect(image)
        high_conf = filter_by_confidence(detections, min_confidence=0.5)
        print(f"High confidence: {len(high_conf)}/{len(detections)}")
        ```
    """
    return [d for d in detections if d.confidence >= min_confidence]


def filter_by_size(
    detections: list[Detection],
    min_width: float = 10.0,
    min_height: float = 10.0,
    min_area: Optional[float] = None,
) -> list[Detection]:
    """
    Filter detections by minimum bbox size.

    This removes very small detections that are likely noise or
    detection artifacts.

    Args:
        detections: List of Detection objects
        min_width: Minimum bbox width in pixels (default: 10.0)
        min_height: Minimum bbox height in pixels (default: 10.0)
        min_area: Minimum bbox area in pixels² (optional)

    Returns:
        Filtered list of detections

    **Example:**
        ```python
        from project_b.layout.postprocessing import filter_by_size

        detections = detector.detect(image)
        filtered = filter_by_size(detections, min_width=20, min_height=20)
        print(f"Removed {len(detections) - len(filtered)} small detections")
        ```
    """
    filtered = []

    for det in detections:
        x, y, width, height = det.bbox

        # Check width/height thresholds
        if width < min_width or height < min_height:
            continue

        # Check area threshold if specified
        if min_area is not None:
            area = width * height
            if area < min_area:
                continue

        filtered.append(det)

    return filtered


def assign_reading_order(
    detections: list[Detection],
    method: str = "top_to_bottom",
) -> list[Detection]:
    """
    Assign reading order indices to detections.

    This is a simplified reading order assignment based on spatial layout.
    For more sophisticated reading order (multi-column, complex layouts),
    see Phase 2 implementation.

    Args:
        detections: List of Detection objects
        method: Reading order method:
            - "top_to_bottom": Sort by y-coordinate (top to bottom)
            - "left_to_right": Sort by x-coordinate (left to right)
            - "natural": Sort by y first, then x (natural reading order)

    Returns:
        List of detections with reading_order_index assigned

    **Example:**
        ```python
        from project_b.layout.postprocessing import assign_reading_order

        detections = detector.detect(image)
        ordered = assign_reading_order(detections, method="natural")

        for det in ordered:
            print(f"{det.reading_order_index}: {det.class_label.value}")
        ```

    **Note:**
    This is a Phase 1 placeholder. Phase 2 will implement sophisticated
    reading order prediction with support for:
    - Multi-column layouts
    - Sidebars and callout boxes
    - Figure/table placement
    - RTL/LTR language support
    """
    if not detections:
        return []

    # Define sorting key based on method
    if method == "top_to_bottom":
        # Sort by y-coordinate (top to bottom)
        key_func = lambda d: d.bbox[1]  # y coordinate
    elif method == "left_to_right":
        # Sort by x-coordinate (left to right)
        key_func = lambda d: d.bbox[0]  # x coordinate
    elif method == "natural":
        # Sort by y first, then x (natural reading order)
        key_func = lambda d: (d.bbox[1], d.bbox[0])  # (y, x)
    else:
        raise ValueError(
            f"Unknown reading order method: {method}. "
            f"Supported: 'top_to_bottom', 'left_to_right', 'natural'"
        )

    # Sort detections
    sorted_detections = sorted(detections, key=key_func)

    # Assign reading order indices
    # Note: We don't modify the Detection objects directly (they're immutable Pydantic models)
    # Instead, return sorted list and use enumerate for reading order downstream

    return sorted_detections


def remove_overlapping_classes(
    detections: list[Detection],
    class_priority: Optional[dict[int, int]] = None,
    iou_threshold: float = 0.7,
) -> list[Detection]:
    """
    Remove overlapping detections from different classes based on priority.

    When two detections of different classes overlap significantly,
    keep only the one from the higher-priority class.

    Args:
        detections: List of Detection objects
        class_priority: Dict mapping class_id to priority (lower = higher priority).
            If None, uses default DocLayNet priorities.
        iou_threshold: IoU threshold for overlap (default: 0.7)

    Returns:
        Filtered list of detections

    **Default Priorities** (lower = higher priority):
    - Title: 1 (highest)
    - Section headers: 2
    - Tables/Figures: 3
    - Text: 4 (lowest)

    **Example:**
        ```python
        from project_b.layout.postprocessing import remove_overlapping_classes

        detections = detector.detect(image)
        cleaned = remove_overlapping_classes(detections, iou_threshold=0.7)
        ```

    **Use Case:**
    Sometimes layout detection models produce overlapping predictions
    (e.g., "title" overlapping with "text"). This function resolves
    such conflicts based on class priority.
    """
    if not detections:
        return []

    # Default DocLayNet class priorities
    if class_priority is None:
        class_priority = {
            10: 1,  # title (highest priority)
            7: 2,   # section_header
            8: 3,   # table
            6: 4,   # picture
            2: 5,   # formula
            0: 6,   # caption
            3: 7,   # list_item
            9: 8,   # text (lower priority)
            1: 9,   # footnote
            4: 10,  # page_footer
            5: 11,  # page_header (lowest priority)
        }

    # Sort by priority
    sorted_detections = sorted(
        detections,
        key=lambda d: class_priority.get(d.class_id, 999)
    )

    # Track which detections to keep
    keep = []
    suppressed = set()

    for i, det_i in enumerate(sorted_detections):
        if i in suppressed:
            continue

        # Keep this detection
        keep.append(det_i)

        # Suppress lower-priority overlapping detections
        for j, det_j in enumerate(sorted_detections[i + 1 :], start=i + 1):
            if j in suppressed:
                continue

            # Compute IoU
            iou = compute_iou(det_i.bbox, det_j.bbox)

            # Suppress if IoU exceeds threshold
            if iou > iou_threshold:
                suppressed.add(j)

    return keep
