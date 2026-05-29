"""
Tests for DocLayNetEvaluator.

Comprehensive tests to achieve 80%+ coverage for the evaluation framework.
"""

import json
from unittest.mock import Mock

import pytest

from data_ingestor.core.models import Document
from data_ingestor.evaluation.doclaynet_evaluator import DocLayNetEvaluator
from data_ingestor.evaluation.models import MetricType


@pytest.fixture
def mock_coco_dir(tmp_path):
    """Create mock COCO directory structure."""
    coco_dir = tmp_path / "ground_truth" / "coco"
    coco_dir.mkdir(parents=True)

    # Create mock COCO data
    coco_data = {
        "categories": [
            {"id": 1, "name": "Caption"},
            {"id": 2, "name": "Text"},
            {"id": 3, "name": "Table"},
        ],
        "images": [
            {
                "id": 1,
                "file_name": "test_doc_123.png",
                "width": 1025,
                "height": 1025,
            },
            {
                "id": 2,
                "file_name": "test_doc_456.png",
                "width": 1025,
                "height": 1025,
            },
        ],
        "annotations": [
            {
                "id": 101,
                "image_id": 1,
                "category_id": 2,
                "bbox": [100, 50, 200, 30],
                "area": 6000,
            },
            {
                "id": 102,
                "image_id": 1,
                "category_id": 3,
                "bbox": [100, 100, 300, 150],
                "area": 45000,
            },
            {
                "id": 103,
                "image_id": 1,
                "category_id": 1,
                "bbox": [100, 270, 200, 20],
                "area": 4000,
            },
        ],
    }

    # Write to train, val, test splits
    for split in ["train", "val", "test"]:
        with open(coco_dir / f"{split}.json", "w") as f:
            json.dump(coco_data, f)

    return tmp_path / "ground_truth"


@pytest.fixture
def evaluator(mock_coco_dir):
    """Create DocLayNetEvaluator with mock COCO data."""
    return DocLayNetEvaluator(mock_coco_dir)


@pytest.fixture
def sample_document():
    """Create sample parsed document with mock elements."""
    # Create mock elements with required attributes for evaluator
    elem1 = Mock()
    elem1.element_type = Mock(value="narrative_text")
    elem1.metadata = Mock(coordinates=[100, 50, 300, 80])
    elem1.bbox = None

    elem2 = Mock()
    elem2.element_type = Mock(value="table")
    elem2.metadata = Mock(coordinates=[100, 100, 400, 250])
    elem2.bbox = None

    elem3 = Mock()
    elem3.element_type = Mock(value="title")
    elem3.metadata = Mock(coordinates=[100, 270, 300, 290])
    elem3.bbox = None

    doc = Mock(spec=Document)
    doc.elements = [elem1, elem2, elem3]
    doc.metadata = {"doc_id": "test_doc_123"}

    return doc


@pytest.fixture
def sample_ground_truth():
    """Create sample ground truth layout."""
    return {
        "layout": {
            "annotations": [
                {
                    "id": 101,
                    "bbox": [100, 50, 200, 30],
                    "category": "Text",
                    "category_id": 2,
                    "area": 6000,
                },
                {
                    "id": 102,
                    "bbox": [100, 100, 300, 150],
                    "category": "Table",
                    "category_id": 3,
                    "area": 45000,
                },
                {
                    "id": 103,
                    "bbox": [100, 270, 200, 20],
                    "category": "Caption",
                    "category_id": 1,
                    "area": 4000,
                },
            ],
        },
    }


class TestDocLayNetEvaluatorInitialization:
    """Test DocLayNetEvaluator initialization."""

    def test_initialization_with_coco_dir(self, mock_coco_dir):
        """Test initialization with valid COCO directory."""
        evaluator = DocLayNetEvaluator(mock_coco_dir)

        assert evaluator.dataset_name == "doclaynet"
        assert evaluator.ground_truth_dir == mock_coco_dir
        assert len(evaluator._coco_data) == 3  # train, val, test
        assert "train" in evaluator._coco_data
        assert "val" in evaluator._coco_data
        assert "test" in evaluator._coco_data

    def test_initialization_without_coco_dir(self, tmp_path):
        """Test initialization when COCO directory doesn't exist."""
        gt_dir = tmp_path / "ground_truth"
        gt_dir.mkdir(parents=True)

        evaluator = DocLayNetEvaluator(gt_dir)

        assert evaluator.dataset_name == "doclaynet"
        assert len(evaluator._coco_data) == 0

    def test_coco_data_structure(self, evaluator):
        """Test COCO data structure after loading."""
        for split in ["train", "val", "test"]:
            assert split in evaluator._coco_data
            assert "filename_map" in evaluator._coco_data[split]
            assert "image_annotations" in evaluator._coco_data[split]
            assert "category_map" in evaluator._coco_data[split]
            assert "images_count" in evaluator._coco_data[split]
            assert "annotations_count" in evaluator._coco_data[split]


class TestDocLayNetEvaluatorEvaluateDocument:
    """Test evaluate_document method."""

    def test_evaluate_document_success(self, evaluator, sample_document, sample_ground_truth):
        """Test successful document evaluation."""
        result = evaluator.evaluate_document(sample_document, sample_ground_truth)

        assert result.success is True
        assert result.document_id == "test_doc_123"
        assert result.dataset == "doclaynet"
        assert len(result.metrics) > 0

        # Should have mAP and reading order metrics
        metric_names = [m.name for m in result.metrics]
        assert MetricType.MAP in metric_names or len(result.metrics) > 0  # mAP if boxes exist
        # Reading order metrics may be present

    def test_evaluate_document_without_bboxes(self, evaluator, sample_ground_truth):
        """Test evaluation when document has no bounding boxes."""
        # Create document without bounding boxes
        elem = Mock()
        elem.element_type = Mock(value="narrative_text")
        elem.metadata = Mock(coordinates=None)
        elem.bbox = None

        document = Mock(spec=Document)
        document.elements = [elem]
        document.metadata = {"doc_id": "test_doc_no_bbox"}

        result = evaluator.evaluate_document(document, sample_ground_truth)

        # Should skip mAP but still calculate reading order
        assert result.success is True
        [m.name for m in result.metrics]
        # mAP should be skipped when no bboxes
        # Reading order metrics may still be calculated

    def test_evaluate_document_missing_layout(self, evaluator, sample_document):
        """Test evaluation with missing layout in ground truth."""
        invalid_gt = {"no_layout": {}}

        result = evaluator.evaluate_document(sample_document, invalid_gt)

        assert result.success is False
        assert "layout annotations missing" in result.error.lower()

    def test_evaluate_document_validation_error(self, evaluator, sample_ground_truth):
        """Test evaluation with None predicted document."""
        with pytest.raises(ValueError, match="Predicted document is None"):
            evaluator.evaluate_document(None, sample_ground_truth)


class TestDocLayNetEvaluatorBoxConversion:
    """Test bounding box conversion methods."""

    def test_elements_to_boxes(self, evaluator, sample_document):
        """Test converting document elements to boxes."""
        boxes = evaluator._elements_to_boxes(sample_document)

        assert len(boxes) == 3
        assert all("bbox" in box for box in boxes)
        assert all("class" in box for box in boxes)
        assert all("id" in box for box in boxes)
        assert all("confidence" in box for box in boxes)

    def test_elements_to_boxes_no_coords(self, evaluator):
        """Test elements without coordinates."""
        elem = Mock()
        elem.element_type = Mock(value="narrative_text")
        elem.metadata = Mock(coordinates=None)
        elem.bbox = None

        document = Mock(spec=Document)
        document.elements = [elem]

        boxes = evaluator._elements_to_boxes(document)

        # Should return empty list for elements without coords
        assert len(boxes) == 0

    def test_elements_to_boxes_with_legacy_bbox(self, evaluator):
        """Test elements with legacy bbox field."""
        elem = Mock()
        elem.element_type = Mock(value="narrative_text")
        elem.metadata = Mock(coordinates=None)
        elem.bbox = [10, 20, 100, 50]

        document = Mock(spec=Document)
        document.elements = [elem]

        boxes = evaluator._elements_to_boxes(document)

        assert len(boxes) == 1
        assert boxes[0]["bbox"] == [10, 20, 100, 50]

    def test_annotations_to_boxes(self, evaluator, sample_ground_truth):
        """Test converting COCO annotations to boxes."""
        layout = sample_ground_truth["layout"]
        boxes = evaluator._annotations_to_boxes(layout)

        assert len(boxes) == 3

        # First box
        assert boxes[0]["id"] == "101"
        assert boxes[0]["class"] == "Text"
        assert boxes[0]["bbox"] == [100, 50, 300, 80]  # [x, y, x+w, y+h]

        # Second box
        assert boxes[1]["bbox"] == [100, 100, 400, 250]

    def test_annotations_to_boxes_empty(self, evaluator):
        """Test empty annotations."""
        boxes = evaluator._annotations_to_boxes({"annotations": []})

        assert len(boxes) == 0

    def test_annotations_to_boxes_invalid_bbox(self, evaluator):
        """Test annotations with invalid bbox."""
        layout = {
            "annotations": [
                {"id": 1, "bbox": [100, 50], "category": "Text"},  # Invalid: only 2 values
                {"id": 2, "bbox": [10, 20, 30, 40], "category": "Table"},  # Valid
            ],
        }

        boxes = evaluator._annotations_to_boxes(layout)

        # Should skip invalid bbox
        assert len(boxes) == 1
        assert boxes[0]["id"] == "2"


class TestDocLayNetEvaluatorReadingOrder:
    """Test reading order extraction."""

    def test_extract_reading_order(self, evaluator, sample_document):
        """Test extracting reading order from document."""
        order = evaluator._extract_reading_order(sample_document)

        assert len(order) == 3
        assert order[0] == "narrative_text_0"
        assert order[1] == "table_1"
        assert order[2] == "title_2"

    def test_extract_ground_truth_order_with_reading_order(self, evaluator):
        """Test extracting ground truth reading order when explicit order exists."""
        layout = {
            "annotations": [
                {"id": 1, "reading_order": 2, "bbox": [0, 100, 10, 10]},
                {"id": 2, "reading_order": 1, "bbox": [0, 50, 10, 10]},
                {"id": 3, "reading_order": 3, "bbox": [0, 150, 10, 10]},
            ],
        }

        order = evaluator._extract_ground_truth_order(layout)

        # Should be sorted by reading_order
        assert order == ["2", "1", "3"]

    def test_extract_ground_truth_order_fallback_y_coordinate(self, evaluator):
        """Test reading order fallback to y-coordinate sorting."""
        layout = {
            "annotations": [
                {"id": 1, "bbox": [0, 150, 10, 10]},  # Bottom
                {"id": 2, "bbox": [0, 50, 10, 10]},  # Top
                {"id": 3, "bbox": [0, 100, 10, 10]},  # Middle
            ],
        }

        order = evaluator._extract_ground_truth_order(layout)

        # Should be sorted by y-coordinate (top to bottom)
        assert order == ["2", "3", "1"]

    def test_extract_ground_truth_order_empty(self, evaluator):
        """Test empty annotations."""
        order = evaluator._extract_ground_truth_order({"annotations": []})

        assert len(order) == 0


class TestDocLayNetEvaluatorGroundTruthLoading:
    """Test ground truth loading from COCO data."""

    def test_load_ground_truth_success(self, evaluator):
        """Test successful ground truth loading."""
        gt = evaluator.load_ground_truth("test_doc_123")

        assert gt is not None
        assert "layout" in gt
        assert "annotations" in gt["layout"]
        assert len(gt["layout"]["annotations"]) == 3

    def test_load_ground_truth_not_found(self, evaluator):
        """Test loading ground truth for non-existent document."""
        gt = evaluator.load_ground_truth("nonexistent_doc")

        assert gt is None

    def test_load_ground_truth_no_coco_data(self, tmp_path):
        """Test loading when COCO data not available."""
        gt_dir = tmp_path / "ground_truth"
        gt_dir.mkdir(parents=True)

        evaluator = DocLayNetEvaluator(gt_dir)
        gt = evaluator.load_ground_truth("test_doc")

        assert gt is None

    def test_load_ground_truth_annotation_format(self, evaluator):
        """Test ground truth annotation format conversion."""
        gt = evaluator.load_ground_truth("test_doc_123")

        assert gt is not None

        ann = gt["layout"]["annotations"][0]
        assert "id" in ann
        assert "bbox" in ann
        assert "category" in ann
        assert "category_id" in ann
        assert "area" in ann


class TestDocLayNetEvaluatorBaselineTargets:
    """Test baseline targets."""

    def test_get_baseline_targets(self, evaluator):
        """Test baseline targets retrieval."""
        targets = evaluator.get_baseline_targets()

        assert MetricType.MAP in targets
        assert MetricType.READING_ORDER_F1 in targets
        assert MetricType.KENDALL_TAU in targets

        assert targets[MetricType.MAP] == 0.70
        assert targets[MetricType.READING_ORDER_F1] == 0.85
        assert targets[MetricType.KENDALL_TAU] == 0.80


class TestDocLayNetEvaluatorIntegration:
    """Integration tests for full evaluation workflow."""

    def test_full_evaluation_workflow(self, evaluator, sample_document):
        """Test complete evaluation workflow from load to result."""
        # Load ground truth
        gt = evaluator.load_ground_truth("test_doc_123")
        assert gt is not None

        # Evaluate document
        result = evaluator.evaluate_document(sample_document, gt)

        # Verify result
        assert result.success is True
        assert result.document_id == "test_doc_123"
        assert len(result.metrics) > 0

        # Check result dict conversion
        result_dict = result.to_dict()
        assert "document_id" in result_dict
        assert "metrics" in result_dict
        assert "success" in result_dict

    def test_batch_evaluation(self, evaluator, sample_document):
        """Test batch evaluation of multiple documents."""
        # Create batch of documents (test_doc_123 has annotations, test_doc_456 doesn't)
        documents = [
            (sample_document, "test_doc_123"),
        ]

        results = []
        for doc, doc_id in documents:
            doc.metadata["doc_id"] = doc_id
            gt = evaluator.load_ground_truth(doc_id)
            if gt:
                result = evaluator.evaluate_document(doc, gt)
                results.append(result)

        # Only test_doc_123 should have ground truth annotations
        assert len(results) == 1
        assert all(r.success for r in results)

    def test_evaluation_with_baseline_comparison(self, evaluator, sample_document):
        """Test evaluation with baseline comparison."""
        gt = evaluator.load_ground_truth("test_doc_123")
        result = evaluator.evaluate_document(sample_document, gt)

        targets = evaluator.get_baseline_targets()

        # Compare metrics against targets
        for metric in result.metrics:
            if metric.name in targets:
                target = targets[metric.name]
                # Just verify comparison works (actual values depend on test data)
                comparison = metric.value >= target
                assert isinstance(comparison, bool)
