"""
Evaluation module for layout detection validation.

This module provides metrics computation and validation scripts for evaluating
layout detection performance on DocLayNet and other COCO-format datasets.

**Key Components:**
- Metrics: mAP, AP, precision, recall, F1, confusion matrix
- Validator: DocLayNet validation script with CLI
- Report generation: HTML/JSON/CSV output formats

**Usage Example:**
    ```python
    from project_b.evaluation import compute_map, validate_on_dataset
    from project_b.layout import YOLODetector

    # Load detector
    detector = YOLODetector("models/yolov10m.pt")

    # Run validation
    results = validate_on_dataset(
        detector=detector,
        dataset_path=Path("data/doclaynet"),
        annotations_path=Path("data/doclaynet/val.json"),
        iou_threshold=0.5
    )

    print(f"mAP@0.50: {results['mAP']:.3f}")
    ```

**CLI Usage:**
    ```bash
    python -m project_b.evaluation.validator \
        --model models/yolov10m.pt \
        --dataset data/doclaynet \
        --annotations data/doclaynet/val.json \
        --output results/report.json
    ```

Schema Version: 1.0.0
"""

from project_b.evaluation.metrics import (
    compute_average_precision,
    compute_confusion_matrix,
    compute_map,
    compute_per_class_metrics,
    compute_precision_recall_f1,
    match_detections_to_ground_truth,
)
from project_b.evaluation.reporter import (
    generate_csv_report,
    generate_html_report,
    save_report,
)
from project_b.evaluation.validator import (
    coco_annotation_to_detection,
    load_coco_annotations,
    print_validation_summary,
    validate_on_dataset,
)

__all__ = [
    # Metrics
    "compute_precision_recall_f1",
    "match_detections_to_ground_truth",
    "compute_average_precision",
    "compute_map",
    "compute_confusion_matrix",
    "compute_per_class_metrics",
    # Reporter
    "generate_html_report",
    "generate_csv_report",
    "save_report",
    # Validator
    "load_coco_annotations",
    "coco_annotation_to_detection",
    "validate_on_dataset",
    "print_validation_summary",
]
