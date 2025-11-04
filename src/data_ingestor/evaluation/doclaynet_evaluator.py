"""
DocLayNet dataset evaluator.

Evaluates layout detection and reading order across 11 document element classes.

Metrics:
- mAP: mean Average Precision across 11 layout classes
- Reading Order F1: Sequence correctness
- Kendall tau: Rank correlation for element ordering
"""

from pathlib import Path
from typing import Dict, List

from data_ingestor.core.models import Document
from data_ingestor.evaluation.base import BaseEvaluator
from data_ingestor.evaluation.models import EvaluationResult, MetricScore, MetricType
from data_ingestor.evaluation.metrics import (
    calculate_kendall_tau,
    calculate_map,
    calculate_reading_order_f1,
)


class DocLayNetEvaluator(BaseEvaluator):
    """
    Evaluator for DocLayNet dataset (layout and reading order).

    DocLayNet provides human-annotated layout labels for 11 element classes
    across diverse document types (financial reports, manuals, patents, papers).

    Layout classes:
    1. Caption      7. Picture
    2. Footnote     8. Section-header
    3. Formula      9. Table
    4. List-item   10. Text
    5. Page-footer 11. Title
    6. Page-header
    """

    def __init__(self, ground_truth_dir: Path):
        """
        Initialize DocLayNet evaluator.

        Args:
            ground_truth_dir: Path to DocLayNet ground truth annotations (JSON)
        """
        super().__init__("doclaynet", ground_truth_dir)

    def evaluate_document(
        self,
        predicted: Document,
        ground_truth: Dict,
    ) -> EvaluationResult:
        """
        Evaluate a document against DocLayNet ground truth.

        Args:
            predicted: Parsed document from our pipeline
            ground_truth: Dict with 'layout' annotations (COCO format)

        Returns:
            EvaluationResult with layout and reading order metrics
        """
        # Validate inputs
        self.validate_document(predicted, ground_truth)

        doc_id = predicted.metadata.get("doc_id", "unknown")
        result = EvaluationResult(
            document_id=doc_id,
            dataset=self.dataset_name,
        )

        try:
            # Extract layout annotations
            gt_layout = ground_truth.get("layout", {})
            if not gt_layout:
                raise ValueError("Ground truth layout annotations missing")

            # Convert document elements to layout boxes
            pred_boxes = self._elements_to_boxes(predicted)
            gt_boxes = self._annotations_to_boxes(gt_layout)

            # Calculate mAP for layout detection
            map_score = calculate_map(pred_boxes, gt_boxes, iou_threshold=0.5)

            result.metrics.append(
                MetricScore(
                    name=MetricType.MAP,
                    value=map_score,
                    metadata={
                        "iou_threshold": 0.5,
                        "pred_boxes": len(pred_boxes),
                        "gt_boxes": len(gt_boxes),
                    },
                )
            )

            # Calculate reading order metrics
            pred_order = self._extract_reading_order(predicted)
            gt_order = self._extract_ground_truth_order(gt_layout)

            if pred_order and gt_order:
                reading_order_f1 = calculate_reading_order_f1(
                    pred_order, gt_order
                )
                kendall_tau = calculate_kendall_tau(pred_order, gt_order)

                result.metrics.extend(
                    [
                        MetricScore(
                            name=MetricType.READING_ORDER_F1,
                            value=reading_order_f1,
                            metadata={
                                "pred_elements": len(pred_order),
                                "gt_elements": len(gt_order),
                            },
                        ),
                        MetricScore(
                            name=MetricType.KENDALL_TAU,
                            value=kendall_tau,
                        ),
                    ]
                )

        except Exception as e:
            result.success = False
            result.error = str(e)

        return result

    def _elements_to_boxes(self, document: Document) -> List[Dict]:
        """
        Convert document elements to bounding boxes for mAP calculation.

        Args:
            document: Parsed document

        Returns:
            List of boxes with class and bbox coordinates
        """
        boxes = []

        for i, element in enumerate(document.elements):
            # Extract bounding box from metadata
            # #ASSUME: Elements have bounding box coordinates in metadata
            # #VERIFY: Bounding box format is [x1, y1, x2, y2]
            bbox = element.metadata.get("bbox", element.metadata.get("coordinates"))

            if bbox:
                boxes.append(
                    {
                        "id": f"{element.category}_{i}",
                        "class": element.type,
                        "bbox": bbox,
                        "confidence": 1.0,  # Default confidence
                    }
                )

        return boxes

    def _annotations_to_boxes(self, layout: Dict) -> List[Dict]:
        """
        Convert COCO-format annotations to boxes.

        Args:
            layout: COCO-format layout annotations

        Returns:
            List of boxes
        """
        boxes = []

        annotations = layout.get("annotations", [])
        for ann in annotations:
            bbox = ann.get("bbox", [])
            category = ann.get("category", "unknown")

            if len(bbox) == 4:
                # Convert [x, y, width, height] to [x1, y1, x2, y2]
                x, y, w, h = bbox
                boxes.append(
                    {
                        "id": str(ann.get("id", len(boxes))),
                        "class": category,
                        "bbox": [x, y, x + w, y + h],
                    }
                )

        return boxes

    def _extract_reading_order(self, document: Document) -> List[str]:
        """
        Extract reading order from document elements.

        Args:
            document: Parsed document

        Returns:
            List of element IDs in reading order
        """
        # Elements are assumed to be in reading order from parser
        return [f"{elem.category}_{i}" for i, elem in enumerate(document.elements)]

    def _extract_ground_truth_order(self, layout: Dict) -> List[str]:
        """
        Extract ground truth reading order.

        Args:
            layout: Layout annotations with reading order

        Returns:
            List of element IDs in correct reading order
        """
        annotations = layout.get("annotations", [])

        # Sort by reading order if available, otherwise by y-coordinate
        if annotations and "reading_order" in annotations[0]:
            annotations = sorted(annotations, key=lambda a: a.get("reading_order", 0))
        else:
            # Fallback: sort by y-coordinate (top-to-bottom)
            annotations = sorted(
                annotations,
                key=lambda a: a.get("bbox", [0, 0, 0, 0])[1],  # y-coordinate
            )

        return [str(ann.get("id", i)) for i, ann in enumerate(annotations)]

    def get_baseline_targets(self) -> Dict[str, float]:
        """Get DocLayNet baseline targets from Phase 1.5 config."""
        return {
            MetricType.MAP: 0.70,
            MetricType.READING_ORDER_F1: 0.85,
            MetricType.KENDALL_TAU: 0.80,
        }
