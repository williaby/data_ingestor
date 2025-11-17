"""
DocLayNet validation script for layout detection evaluation.

This script evaluates a YOLOv10 layout detector on the DocLayNet dataset
(or any COCO-format dataset) and generates comprehensive performance reports.

**Usage:**
    ```bash
    # Run validation
    python -m project_b.evaluation.validator \
        --model models/yolov10m_doclaynet.pt \
        --dataset data/doclaynet \
        --annotations data/doclaynet/val.json \
        --output results/validation_report.json

    # With specific options
    python -m project_b.evaluation.validator \
        --model models/yolov10m.pt \
        --dataset data/doclaynet \
        --annotations data/doclaynet/val.json \
        --output results/report.json \
        --confidence 0.3 \
        --iou-threshold 0.5 \
        --max-images 100 \
        --device cuda
    ```

**Expected Dataset Structure:**
    ```
    data/doclaynet/
    ├── images/
    │   ├── image001.png
    │   ├── image002.png
    │   └── ...
    └── annotations/
        └── val.json  # COCO format annotations
    ```

**COCO Annotation Format:**
    ```json
    {
        "images": [
            {"id": 1, "file_name": "image001.png", "width": 1024, "height": 1024}
        ],
        "annotations": [
            {
                "id": 1,
                "image_id": 1,
                "category_id": 10,  # DocLayNet class (0-10)
                "bbox": [x, y, width, height],  # COCO format
                "area": 5000,
                "iscrowd": 0
            }
        ],
        "categories": [
            {"id": 0, "name": "caption"},
            {"id": 1, "name": "footnote"},
            ...
        ]
    }
    ```
"""

import argparse
import json
import time
from pathlib import Path
from typing import Any, Optional

import numpy as np
from PIL import Image
from tqdm import tqdm

from project_b.layout.detector import DOCLAYNET_CLASS_MAPPING, Detection, YOLODetector
from project_b.layout.postprocessing import apply_nms, filter_by_confidence
from project_b.evaluation.metrics import (
    compute_confusion_matrix,
    compute_map,
    compute_per_class_metrics,
)
from project_b.evaluation.reporter import save_report


def load_coco_annotations(
    annotations_path: Path,
) -> tuple[dict[int, dict[str, Any]], dict[int, list[dict[str, Any]]]]:
    """
    Load COCO format annotations.

    Args:
        annotations_path: Path to COCO JSON annotations file

    Returns:
        Tuple of (images_dict, annotations_dict):
        - images_dict: Maps image_id -> image metadata
        - annotations_dict: Maps image_id -> list of annotations

    Raises:
        FileNotFoundError: If annotations file doesn't exist
        ValueError: If JSON format is invalid
    """
    if not annotations_path.exists():
        raise FileNotFoundError(f"Annotations file not found: {annotations_path}")

    with open(annotations_path) as f:
        coco_data = json.load(f)

    # Build images dictionary
    images_dict = {img["id"]: img for img in coco_data["images"]}

    # Build annotations dictionary (group by image_id)
    annotations_dict = {}
    for ann in coco_data["annotations"]:
        image_id = ann["image_id"]
        if image_id not in annotations_dict:
            annotations_dict[image_id] = []
        annotations_dict[image_id].append(ann)

    return images_dict, annotations_dict


def coco_annotation_to_detection(ann: dict[str, Any]) -> Detection:
    """
    Convert COCO annotation to Detection object.

    Args:
        ann: COCO annotation dictionary with keys:
            - category_id: Class ID (0-10 for DocLayNet)
            - bbox: [x, y, width, height] in COCO format

    Returns:
        Detection object with confidence=1.0 (ground truth)
    """
    class_id = ann["category_id"]

    # Map class_id to ClassLabelEnum
    if class_id not in DOCLAYNET_CLASS_MAPPING:
        raise ValueError(
            f"Invalid class_id: {class_id}. "
            f"DocLayNet supports 0-10, got {class_id}"
        )

    class_label = DOCLAYNET_CLASS_MAPPING[class_id]

    return Detection(
        bbox=ann["bbox"],  # Already in COCO format [x, y, w, h]
        confidence=1.0,  # Ground truth
        class_id=class_id,
        class_label=class_label,
    )


def validate_on_dataset(
    detector: YOLODetector,
    dataset_path: Path,
    annotations_path: Path,
    confidence_threshold: float = 0.3,
    iou_threshold: float = 0.5,
    nms_threshold: float = 0.45,
    max_images: Optional[int] = None,
    verbose: bool = True,
) -> dict[str, Any]:
    """
    Run validation on a COCO-format dataset.

    Args:
        detector: YOLODetector instance
        dataset_path: Path to dataset root directory (contains images/)
        annotations_path: Path to COCO annotations JSON
        confidence_threshold: Minimum detection confidence
        iou_threshold: IoU threshold for evaluation matching
        nms_threshold: NMS IoU threshold for postprocessing
        max_images: Maximum number of images to process (None = all)
        verbose: Show progress bar

    Returns:
        Dictionary with validation results:
        - "mAP": Overall mAP@IoU
        - "AP_class_{id}": Per-class AP
        - "per_class_metrics": Precision/Recall/F1 per class
        - "confusion_matrix": Confusion matrix
        - "total_images": Number of images processed
        - "total_detections": Number of detections made
        - "total_ground_truths": Number of ground truth boxes
        - "avg_inference_time_ms": Average inference time per image

    Raises:
        FileNotFoundError: If dataset or annotations not found
    """
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset path not found: {dataset_path}")

    # Load annotations
    if verbose:
        print(f"Loading annotations from {annotations_path}...")

    images_dict, annotations_dict = load_coco_annotations(annotations_path)

    # Limit number of images if specified
    image_ids = list(images_dict.keys())
    if max_images is not None:
        image_ids = image_ids[:max_images]

    if verbose:
        print(f"Validating on {len(image_ids)} images...")

    # Collect all predictions and ground truths
    all_predictions = []
    all_ground_truths = []
    inference_times = []

    # Process each image
    iterator = tqdm(image_ids, desc="Validating") if verbose else image_ids

    for image_id in iterator:
        image_info = images_dict[image_id]
        image_filename = image_info["file_name"]
        image_path = dataset_path / "images" / image_filename

        # Skip if image doesn't exist
        if not image_path.exists():
            if verbose:
                print(f"Warning: Image not found: {image_path}")
            continue

        # Load image
        try:
            image = Image.open(image_path).convert("RGB")
        except Exception as e:
            if verbose:
                print(f"Warning: Failed to load {image_path}: {e}")
            continue

        # Run detection
        start_time = time.time()
        detections = detector.detect(
            image,
            confidence_threshold=confidence_threshold,
            iou_threshold=nms_threshold,
        )
        inference_time_ms = (time.time() - start_time) * 1000
        inference_times.append(inference_time_ms)

        # Apply postprocessing
        detections = apply_nms(detections, iou_threshold=nms_threshold)
        detections = filter_by_confidence(detections, min_confidence=confidence_threshold)

        all_predictions.extend(detections)

        # Load ground truth annotations for this image
        if image_id in annotations_dict:
            gt_annotations = annotations_dict[image_id]
            for ann in gt_annotations:
                try:
                    gt_det = coco_annotation_to_detection(ann)
                    all_ground_truths.append(gt_det)
                except ValueError as e:
                    if verbose:
                        print(f"Warning: Skipping invalid annotation: {e}")

    if verbose:
        print(f"\nProcessed {len(image_ids)} images")
        print(f"Total predictions: {len(all_predictions)}")
        print(f"Total ground truths: {len(all_ground_truths)}")
        print(f"Avg inference time: {np.mean(inference_times):.1f}ms")

    # Compute metrics
    if verbose:
        print("\nComputing metrics...")

    # mAP
    map_results = compute_map(
        all_predictions,
        all_ground_truths,
        iou_threshold=iou_threshold,
    )

    # Per-class metrics
    per_class_metrics = compute_per_class_metrics(
        all_predictions,
        all_ground_truths,
        iou_threshold=iou_threshold,
    )

    # Confusion matrix
    confusion_matrix = compute_confusion_matrix(
        all_predictions,
        all_ground_truths,
        num_classes=11,  # DocLayNet has 11 classes
        iou_threshold=iou_threshold,
    )

    # Compile results
    results = {
        **map_results,
        "per_class_metrics": per_class_metrics,
        "confusion_matrix": confusion_matrix.tolist(),
        "total_images": len(image_ids),
        "total_detections": len(all_predictions),
        "total_ground_truths": len(all_ground_truths),
        "avg_inference_time_ms": float(np.mean(inference_times)) if inference_times else 0.0,
        "inference_times_ms": inference_times,
        "config": {
            "confidence_threshold": confidence_threshold,
            "iou_threshold": iou_threshold,
            "nms_threshold": nms_threshold,
            "max_images": max_images,
        },
    }

    return results


def print_validation_summary(results: dict[str, Any]) -> None:
    """
    Print human-readable validation summary.

    Args:
        results: Validation results dictionary from validate_on_dataset()
    """
    print("\n" + "=" * 80)
    print("VALIDATION RESULTS")
    print("=" * 80)

    # Overall metrics
    print(f"\nmAP@{results['config']['iou_threshold']}: {results['mAP']:.3f}")
    print(f"Total images: {results['total_images']}")
    print(f"Total predictions: {results['total_detections']}")
    print(f"Total ground truths: {results['total_ground_truths']}")
    print(f"Avg inference time: {results['avg_inference_time_ms']:.1f}ms")

    # Per-class AP
    print("\nPer-Class Average Precision:")
    print("-" * 80)
    print(f"{'Class ID':<10} {'Class Name':<20} {'AP':<10}")
    print("-" * 80)

    for class_id in range(11):
        key = f"AP_class_{class_id}"
        if key in results:
            class_name = DOCLAYNET_CLASS_MAPPING[class_id].value
            ap = results[key]
            print(f"{class_id:<10} {class_name:<20} {ap:.3f}")

    # Per-class P/R/F1
    print("\nPer-Class Precision/Recall/F1:")
    print("-" * 80)
    print(f"{'Class ID':<10} {'Precision':<12} {'Recall':<12} {'F1':<10} {'TP':<6} {'FP':<6} {'FN':<6}")
    print("-" * 80)

    per_class = results["per_class_metrics"]
    for class_id in sorted(per_class.keys()):
        metrics = per_class[class_id]
        print(
            f"{class_id:<10} "
            f"{metrics['precision']:.3f}       "
            f"{metrics['recall']:.3f}       "
            f"{metrics['f1']:.3f}     "
            f"{metrics['tp']:<6} "
            f"{metrics['fp']:<6} "
            f"{metrics['fn']:<6}"
        )

    print("=" * 80)


def main():
    """CLI entry point for validation script."""
    parser = argparse.ArgumentParser(
        description="Validate YOLOv10 layout detector on DocLayNet dataset"
    )

    parser.add_argument(
        "--model",
        type=Path,
        required=True,
        help="Path to YOLOv10 model (.pt or .onnx)",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        required=True,
        help="Path to dataset root directory (contains images/)",
    )
    parser.add_argument(
        "--annotations",
        type=Path,
        required=True,
        help="Path to COCO format annotations JSON",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("validation_results.json"),
        help="Output path for results (default: validation_results.json)",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="auto",
        choices=["auto", "json", "html", "csv", "all"],
        help="Output format: auto (from extension), json, html, csv, or all (default: auto)",
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=0.3,
        help="Confidence threshold for detections (default: 0.3)",
    )
    parser.add_argument(
        "--iou-threshold",
        type=float,
        default=0.5,
        help="IoU threshold for evaluation matching (default: 0.5)",
    )
    parser.add_argument(
        "--nms-threshold",
        type=float,
        default=0.45,
        help="NMS IoU threshold (default: 0.45)",
    )
    parser.add_argument(
        "--max-images",
        type=int,
        default=None,
        help="Maximum number of images to process (default: all)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda",
        choices=["cuda", "cpu"],
        help="Device for inference (default: cuda)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output",
    )

    args = parser.parse_args()

    # Load detector
    print(f"Loading model from {args.model}...")
    detector = YOLODetector(str(args.model), device=args.device)

    # Run validation
    results = validate_on_dataset(
        detector=detector,
        dataset_path=args.dataset,
        annotations_path=args.annotations,
        confidence_threshold=args.confidence,
        iou_threshold=args.iou_threshold,
        nms_threshold=args.nms_threshold,
        max_images=args.max_images,
        verbose=not args.quiet,
    )

    # Print summary
    if not args.quiet:
        print_validation_summary(results)

    # Save results
    if args.format == "all":
        # Save in all formats
        print("\nSaving results in all formats...")

        # JSON
        json_path = args.output.with_suffix(".json")
        save_report(results, json_path, format="json")
        print(f"  - JSON: {json_path}")

        # HTML
        html_path = args.output.with_suffix(".html")
        save_report(results, html_path, format="html")
        print(f"  - HTML: {html_path}")

        # CSV
        csv_dir = args.output.with_suffix("")
        csv_files = save_report(results, csv_dir, format="csv")
        print(f"  - CSV: {len(csv_files)} files in {csv_dir}/")
    else:
        # Save in single format
        print(f"\nSaving results to {args.output}...")
        saved_path = save_report(results, args.output, format=args.format)

        if isinstance(saved_path, list):
            # CSV format returns list of files
            print(f"Created {len(saved_path)} CSV files in {args.output}/")
        else:
            print(f"Saved to {saved_path}")

    print("Done!")


if __name__ == "__main__":
    main()
