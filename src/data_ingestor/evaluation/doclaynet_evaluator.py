"""
DocLayNet dataset evaluator.

Evaluates layout detection and reading order across 11 document element classes.

Metrics:
- mAP: mean Average Precision across 11 layout classes
- Reading Order F1: Sequence correctness
- Kendall tau: Rank correlation for element ordering
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from data_ingestor.core.models import Document
from data_ingestor.evaluation.base import BaseEvaluator
from data_ingestor.evaluation.models import EvaluationResult, MetricScore, MetricType
from data_ingestor.evaluation.metrics import (
    calculate_kendall_tau,
    calculate_map,
    calculate_reading_order_f1,
)

logger = logging.getLogger(__name__)

# Mapping from internal element types to DocLayNet COCO categories
# #CRITICAL: This mapping must cover all element types produced by parsers
# #VERIFY: All 11 DocLayNet categories are represented
ELEMENT_TYPE_TO_COCO = {
    "narrative_text": "Text",
    "text": "Text",
    "list_item": "List-item",
    "table": "Table",
    "title": "Title",
    "section_header": "Section-header",
    "caption": "Caption",
    "footnote": "Footnote",
    "formula": "Formula",
    "page_header": "Page-header",
    "page_footer": "Page-footer",
    "picture": "Picture",
    "image": "Picture",
}


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

        # Cache for COCO JSON data (loaded once for efficiency)
        # #ASSUME: COCO files are in ground_truth_dir/coco/
        # #VERIFY: All three splits (train, val, test) are available
        self._coco_data = {}
        self._coco_dir = self.ground_truth_dir / "coco"

        if not self._coco_dir.exists():
            logger.warning(f"COCO directory not found: {self._coco_dir}")
        else:
            self._load_coco_data()

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

            # Calculate mAP for layout detection (only if parser provides bounding boxes)
            # #ASSUME: Parsers without layout detection don't provide bounding boxes
            # #VERIFY: PyMuPDF/PyMuPDF4LLM will have 0 predicted boxes
            if pred_boxes:
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
            else:
                logger.info(
                    f"Skipping mAP calculation for {doc_id}: "
                    f"Parser does not provide bounding boxes"
                )

            # Calculate reading order metrics using bbox matching
            # Match predicted elements to ground truth annotations via IoU
            element_to_annotation_map = self._match_elements_to_annotations(
                predicted, gt_layout, iou_threshold=0.3
            )

            # Extract reading orders (use matched IDs for predicted elements)
            pred_order = self._extract_reading_order(predicted, element_to_annotation_map)
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
            # #ASSUME: Elements have bounding box coordinates in metadata or legacy bbox field
            # #VERIFY: Bounding box format is [x1, y1, x2, y2]
            # #CRITICAL: ElementMetadata is Pydantic model, use attribute access not .get()
            bbox = element.metadata.coordinates or element.bbox

            if bbox:
                # Map internal element type to COCO category
                element_type = element.element_type.value
                coco_category = ELEMENT_TYPE_TO_COCO.get(element_type, element_type)

                boxes.append(
                    {
                        "id": f"{element_type}_{i}",
                        "class": coco_category,  # Use COCO category for matching
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

    def _match_elements_to_annotations(
        self, document: Document, gt_layout: Dict, iou_threshold: float = 0.3
    ) -> Dict[int, str]:
        """
        Match predicted elements to ground truth annotations using bbox IoU.

        Args:
            document: Parsed document with elements
            gt_layout: Ground truth layout annotations
            iou_threshold: Minimum IoU for considering a match

        Returns:
            Dict mapping element index to annotation ID
        """
        from data_ingestor.evaluation.metrics.layout_metrics import _calculate_iou

        element_to_annotation = {}
        annotations = gt_layout.get("annotations", [])

        for i, element in enumerate(document.elements):
            # Get element bbox
            bbox = element.metadata.coordinates or element.bbox
            if not bbox:
                continue

            # Find best matching annotation
            best_iou = 0.0
            best_annotation_id = None

            for ann in annotations:
                gt_bbox = ann.get("bbox", [])
                if len(gt_bbox) != 4:
                    continue

                # Convert COCO format [x, y, w, h] to [x1, y1, x2, y2]
                x, y, w, h = gt_bbox
                gt_bbox_converted = [x, y, x + w, y + h]

                iou = _calculate_iou(bbox, gt_bbox_converted)
                if iou > best_iou:
                    best_iou = iou
                    best_annotation_id = str(ann.get("id"))

            # Map if IoU exceeds threshold
            if best_iou >= iou_threshold and best_annotation_id:
                element_to_annotation[i] = best_annotation_id

        logger.debug(
            f"Matched {len(element_to_annotation)}/{len(document.elements)} "
            f"elements to annotations (IoU >= {iou_threshold})"
        )

        return element_to_annotation

    def _extract_reading_order(
        self, document: Document, element_to_annotation_map: Optional[Dict[int, str]] = None
    ) -> List[str]:
        """
        Extract reading order from document elements.

        Args:
            document: Parsed document
            element_to_annotation_map: Optional mapping from element index to annotation ID

        Returns:
            List of element IDs in reading order
        """
        # If we have a mapping from bbox matching, use annotation IDs
        if element_to_annotation_map:
            return [
                element_to_annotation_map[i]
                for i in range(len(document.elements))
                if i in element_to_annotation_map
            ]

        # Fallback: use element type and index
        # #ASSUME: This will likely produce 0.0 metrics without bbox matching
        return [f"{elem.element_type.value}_{i}" for i, elem in enumerate(document.elements)]

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

    def _load_coco_data(self) -> None:
        """
        Load COCO JSON files and build mapping structures.

        Loads train.json, val.json, test.json and creates:
        - filename → image_id mapping
        - image_id → annotations mapping
        - category_id → category_name mapping
        """
        logger.info("Loading DocLayNet COCO annotations...")

        for split in ["train", "val", "test"]:
            coco_file = self._coco_dir / f"{split}.json"

            if not coco_file.exists():
                logger.warning(f"COCO file not found: {coco_file}")
                continue

            with open(coco_file, "r") as f:
                coco_data = json.load(f)

            # Build filename → image mapping
            filename_map = {}
            for img in coco_data.get("images", []):
                filename_map[img["file_name"]] = img

            # Build image_id → annotations mapping
            image_annotations = {}
            for ann in coco_data.get("annotations", []):
                image_id = ann["image_id"]
                if image_id not in image_annotations:
                    image_annotations[image_id] = []
                image_annotations[image_id].append(ann)

            # Build category_id → category_name mapping
            category_map = {}
            for cat in coco_data.get("categories", []):
                category_map[cat["id"]] = cat["name"]

            self._coco_data[split] = {
                "filename_map": filename_map,
                "image_annotations": image_annotations,
                "category_map": category_map,
                "images_count": len(filename_map),
                "annotations_count": len(coco_data.get("annotations", [])),
            }

            logger.info(
                f"Loaded {split}.json: "
                f"{self._coco_data[split]['images_count']} images, "
                f"{self._coco_data[split]['annotations_count']} annotations"
            )

    def load_ground_truth(self, document_id: str) -> Optional[Dict]:
        """
        Load ground truth for a DocLayNet document from COCO annotations.

        Converts PDF document ID to PNG filename, finds matching image in COCO,
        extracts annotations, and returns in expected format.

        Args:
            document_id: Document identifier (PDF filename without extension)

        Returns:
            Dict with 'layout' key containing 'annotations', or None if not found
        """
        if not self._coco_data:
            logger.error("COCO data not loaded")
            return None

        # Convert PDF doc_id to PNG filename
        # #ASSUME: PNG filename matches PDF filename (both use same hash)
        # #VERIFY: Document exists in one of the COCO splits
        png_filename = f"{document_id}.png"

        # Search all splits for this document
        for split in ["train", "val", "test"]:
            if split not in self._coco_data:
                continue

            split_data = self._coco_data[split]
            filename_map = split_data["filename_map"]

            if png_filename not in filename_map:
                continue

            # Found the image!
            image = filename_map[png_filename]
            image_id = image["id"]

            # Get annotations for this image
            annotations = split_data["image_annotations"].get(image_id, [])
            category_map = split_data["category_map"]

            if not annotations:
                logger.warning(
                    f"No annotations found for {document_id} (image_id={image_id})"
                )
                return None

            # Convert to expected format
            formatted_annotations = []
            for ann in annotations:
                formatted_annotations.append(
                    {
                        "id": ann["id"],
                        "bbox": ann["bbox"],  # [x, y, width, height]
                        "category": category_map.get(
                            ann["category_id"], "unknown"
                        ),
                        "category_id": ann["category_id"],
                        "area": ann.get("area", 0),
                        # Note: DocLayNet doesn't have explicit reading_order
                        # Evaluator will fall back to y-coordinate sorting
                    }
                )

            logger.debug(
                f"Found {len(formatted_annotations)} annotations for "
                f"{document_id} in {split}.json"
            )

            return {"layout": {"annotations": formatted_annotations}}

        # Not found in any split
        logger.error(f"Document {document_id} not found in any COCO split")
        return None
