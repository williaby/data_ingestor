"""
Layout detection module for Project B.

This module implements layout detection using YOLOv10-doc trained on DocLayNet
to identify 11 structural elements (caption, footnote, formula, list_item,
page_footer, page_header, picture, section_header, table, text, title).

**Key Components:**
- YOLODetector: Main detector class for YOLO model inference
- Detection: Pydantic model for detection results
- Postprocessing: NMS, filtering, and bbox refinement utilities

**Performance Targets** (ADR-0005):
- mAP@0.50 e 0.84 on DocLayNet
- Latency: 50-100ms/page on GPU, <300ms on CPU

**Model Support:**
- ONNX Runtime (recommended for production)
- PyTorch (for development/training)

**Example Usage:**
    ```python
    from project_b.layout import YOLODetector, apply_nms, filter_by_confidence
    from PIL import Image

    # Initialize detector
    detector = YOLODetector("models/yolov10m_doclaynet.pt", device="cuda")

    # Detect layout elements
    image = Image.open("document_page.png")
    detections = detector.detect(image, confidence_threshold=0.3)

    # Apply postprocessing
    detections = apply_nms(detections, iou_threshold=0.45)
    detections = filter_by_confidence(detections, min_confidence=0.5)

    # Print results
    for det in detections:
        print(f"{det.class_label.value}: {det.confidence:.2f}, bbox: {det.bbox}")
    ```

Schema Version: 1.0.0
"""

from project_b.layout.detector import Detection, YOLODetector
from project_b.layout.postprocessing import (
    apply_nms,
    assign_reading_order,
    compute_iou,
    filter_by_confidence,
    filter_by_size,
    remove_overlapping_classes,
)

__all__ = [
    "YOLODetector",
    "Detection",
    "apply_nms",
    "filter_by_confidence",
    "filter_by_size",
    "assign_reading_order",
    "compute_iou",
    "remove_overlapping_classes",
]
