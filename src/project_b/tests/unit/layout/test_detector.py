"""
Unit tests for YOLODetector class.

Tests for model loading, inference, error handling, and device selection.
Uses mocking to avoid requiring actual model files.
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest
from PIL import Image

from project_b.layout.detector import DOCLAYNET_CLASS_MAPPING, Detection, YOLODetector
from project_b.schemas.ocr_document import ClassLabelEnum


class TestYOLODetectorInitialization:
    """Test YOLODetector initialization and model loading."""

    def test_model_path_not_exist_raises_error(self):
        """Test initialization fails if model path doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Model not found"):
            YOLODetector("nonexistent_model.pt")

    def test_unsupported_model_format_raises_error(self, tmp_path):
        """Test initialization fails with unsupported model format."""
        # Create a dummy file with unsupported extension
        model_path = tmp_path / "model.txt"
        model_path.touch()

        with pytest.raises(ValueError, match="Unsupported model format"):
            YOLODetector(str(model_path))

    @patch("ultralytics.YOLO")
    @patch("torch.cuda")
    def test_pytorch_model_loading_success(self, mock_cuda, mock_yolo, tmp_path):
        """Test successful PyTorch model loading."""
        # Create dummy .pt file
        model_path = tmp_path / "yolov10.pt"
        model_path.touch()

        # Mock torch.cuda
        mock_cuda.is_available.return_value = True

        # Mock YOLO model
        mock_model = MagicMock()
        mock_yolo.return_value = mock_model

        # Initialize detector
        detector = YOLODetector(str(model_path), device="cuda")

        # Verify model was loaded
        mock_yolo.assert_called_once_with(str(model_path))
        assert detector.model_type == "pytorch"
        assert detector.device == "cuda"

    @patch("ultralytics.YOLO")
    def test_pytorch_model_cpu_fallback(self, mock_yolo, tmp_path):
        """Test PyTorch model loads on CPU when CUDA unavailable."""
        model_path = tmp_path / "yolov10.pt"
        model_path.touch()

        mock_model = MagicMock()
        mock_yolo.return_value = mock_model

        # Initialize with CPU
        detector = YOLODetector(str(model_path), device="cpu")

        assert detector.device == "cpu"
        mock_model.to.assert_called_with("cpu")

    @patch("onnxruntime.InferenceSession")
    def test_onnx_model_loading_success(self, mock_session_class, tmp_path):
        """Test successful ONNX model loading."""
        model_path = tmp_path / "yolov10.onnx"
        model_path.touch()

        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        # Initialize detector
        detector = YOLODetector(str(model_path), device="cuda")

        # Verify ONNX session was created
        mock_session_class.assert_called_once()
        assert detector.model_type == "onnx"

    def test_pytorch_import_error_handling(self, tmp_path):
        """Test proper error when PyTorch not installed."""
        model_path = tmp_path / "yolov10.pt"
        model_path.touch()

        # Mock the builtins __import__ to raise ImportError for ultralytics
        with patch("builtins.__import__", side_effect=ImportError("No module named 'ultralytics'")):
            with pytest.raises(ImportError, match="PyTorch/Ultralytics not installed"):
                YOLODetector(str(model_path))

    def test_onnx_import_error_handling(self, tmp_path):
        """Test proper error when ONNX Runtime not installed."""
        model_path = tmp_path / "yolov10.onnx"
        model_path.touch()

        # Mock the builtins __import__ to raise ImportError for onnxruntime
        with patch("builtins.__import__", side_effect=ImportError("No module named 'onnxruntime'")):
            with pytest.raises(ImportError, match="ONNX Runtime not installed"):
                YOLODetector(str(model_path))

    @patch("ultralytics.YOLO")
    @patch("torch.cuda")
    def test_cuda_requested_but_unavailable(self, mock_cuda, mock_yolo, tmp_path):
        """Test error when CUDA requested but not available."""
        model_path = tmp_path / "yolov10.pt"
        model_path.touch()

        mock_cuda.is_available.return_value = False
        mock_yolo.return_value = MagicMock()

        with pytest.raises(RuntimeError, match="CUDA requested but not available"):
            YOLODetector(str(model_path), device="cuda")

    @patch("ultralytics.YOLO")
    def test_custom_input_size(self, mock_yolo, tmp_path):
        """Test custom input size configuration."""
        model_path = tmp_path / "yolov10.pt"
        model_path.touch()

        mock_yolo.return_value = MagicMock()

        detector = YOLODetector(str(model_path), device="cpu", input_size=(640, 640))

        assert detector.input_size == (640, 640)


class TestYOLODetectorInference:
    """Test YOLODetector inference (detect method)."""

    @patch("ultralytics.YOLO")
    def test_detect_with_pil_image(self, mock_yolo, tmp_path):
        """Test detection with PIL Image input."""
        model_path = tmp_path / "yolov10.pt"
        model_path.touch()

        # Create mock model and results
        mock_model = MagicMock()
        mock_yolo.return_value = mock_model

        # Create a single mock box object
        mock_box = MagicMock()
        mock_box.xyxy = [Mock(cpu=Mock(return_value=Mock(numpy=Mock(return_value=np.array([10, 20, 110, 120])))))]
        mock_box.conf = [0.95]
        mock_box.cls = [10]  # Title class

        # Create iterable boxes container
        mock_boxes = MagicMock()
        mock_boxes.__iter__ = Mock(return_value=iter([mock_box]))
        mock_boxes.__len__ = Mock(return_value=1)

        mock_result = MagicMock()
        mock_result.boxes = mock_boxes
        mock_model.predict.return_value = [mock_result]

        # Create detector and run inference
        detector = YOLODetector(str(model_path), device="cpu")
        image = Image.new("RGB", (100, 100), color="white")
        detections = detector.detect(image, confidence_threshold=0.3)

        # Verify predict was called
        mock_model.predict.assert_called_once()

        # Verify detection results
        assert len(detections) == 1
        det = detections[0]
        assert det.class_id == 10
        assert det.class_label == ClassLabelEnum.TITLE

    @patch("ultralytics.YOLO")
    def test_detect_with_file_path(self, mock_yolo, tmp_path):
        """Test detection with file path input."""
        model_path = tmp_path / "yolov10.pt"
        model_path.touch()

        # Create test image file
        image_path = tmp_path / "test.png"
        test_image = Image.new("RGB", (100, 100), color="white")
        test_image.save(image_path)

        mock_model = MagicMock()
        mock_yolo.return_value = mock_model

        # Mock empty results
        mock_result = MagicMock()
        mock_result.boxes = None
        mock_model.predict.return_value = [mock_result]

        detector = YOLODetector(str(model_path), device="cpu")
        detections = detector.detect(str(image_path))

        # Should load image and run detection
        mock_model.predict.assert_called_once()
        assert detections == []

    @patch("ultralytics.YOLO")
    def test_detect_with_numpy_array(self, mock_yolo, tmp_path):
        """Test detection with numpy array input."""
        model_path = tmp_path / "yolov10.pt"
        model_path.touch()

        mock_model = MagicMock()
        mock_yolo.return_value = mock_model

        mock_result = MagicMock()
        mock_result.boxes = None
        mock_model.predict.return_value = [mock_result]

        detector = YOLODetector(str(model_path), device="cpu")
        image_array = np.ones((100, 100, 3), dtype=np.uint8) * 255
        detections = detector.detect(image_array)

        mock_model.predict.assert_called_once()
        assert detections == []

    @patch("ultralytics.YOLO")
    def test_detect_invalid_confidence_threshold(self, mock_yolo, tmp_path):
        """Test detection fails with invalid confidence threshold."""
        model_path = tmp_path / "yolov10.pt"
        model_path.touch()

        mock_yolo.return_value = MagicMock()

        detector = YOLODetector(str(model_path), device="cpu")
        image = Image.new("RGB", (100, 100))

        # Confidence too low
        with pytest.raises(ValueError, match="confidence_threshold must be in"):
            detector.detect(image, confidence_threshold=-0.1)

        # Confidence too high
        with pytest.raises(ValueError, match="confidence_threshold must be in"):
            detector.detect(image, confidence_threshold=1.5)

    @patch("ultralytics.YOLO")
    def test_detect_invalid_iou_threshold(self, mock_yolo, tmp_path):
        """Test detection fails with invalid IoU threshold."""
        model_path = tmp_path / "yolov10.pt"
        model_path.touch()

        mock_yolo.return_value = MagicMock()

        detector = YOLODetector(str(model_path), device="cpu")
        image = Image.new("RGB", (100, 100))

        with pytest.raises(ValueError, match="iou_threshold must be in"):
            detector.detect(image, iou_threshold=1.5)

    @patch("ultralytics.YOLO")
    def test_detect_invalid_image_type(self, mock_yolo, tmp_path):
        """Test detection fails with invalid image type."""
        model_path = tmp_path / "yolov10.pt"
        model_path.touch()

        mock_yolo.return_value = MagicMock()

        detector = YOLODetector(str(model_path), device="cpu")

        # Pass an invalid type (not str, Path, ndarray, or Image.Image)
        with pytest.raises(ValueError, match="image must be PIL Image"):
            detector.detect(12345)  # Invalid type

    @patch("ultralytics.YOLO")
    def test_detect_multiple_detections(self, mock_yolo, tmp_path):
        """Test detection with multiple boxes."""
        model_path = tmp_path / "yolov10.pt"
        model_path.touch()

        mock_model = MagicMock()
        mock_yolo.return_value = mock_model

        # Mock multiple detection results
        mock_boxes = MagicMock()

        # Create mock boxes with proper structure
        box1 = MagicMock()
        box1.xyxy = [Mock(cpu=Mock(return_value=Mock(numpy=Mock(return_value=np.array([10, 20, 110, 120])))))]
        box1.conf = [0.95]
        box1.cls = [10]  # Title

        box2 = MagicMock()
        box2.xyxy = [Mock(cpu=Mock(return_value=Mock(numpy=Mock(return_value=np.array([10, 150, 110, 200])))))]
        box2.conf = [0.85]
        box2.cls = [9]  # Text

        # Make boxes iterable
        mock_boxes.__iter__ = Mock(return_value=iter([box1, box2]))
        mock_boxes.__len__ = Mock(return_value=2)

        mock_result = MagicMock()
        mock_result.boxes = mock_boxes
        mock_model.predict.return_value = [mock_result]

        detector = YOLODetector(str(model_path), device="cpu")
        image = Image.new("RGB", (200, 300))
        detections = detector.detect(image)

        # Should have 2 detections
        assert len(detections) == 2

    @patch("ultralytics.YOLO")
    def test_detect_empty_results(self, mock_yolo, tmp_path):
        """Test detection with no boxes found."""
        model_path = tmp_path / "yolov10.pt"
        model_path.touch()

        mock_model = MagicMock()
        mock_yolo.return_value = mock_model

        # Mock empty results
        mock_result = MagicMock()
        mock_result.boxes = None
        mock_model.predict.return_value = [mock_result]

        detector = YOLODetector(str(model_path), device="cpu")
        image = Image.new("RGB", (100, 100))
        detections = detector.detect(image)

        assert detections == []

    @patch("onnxruntime.InferenceSession")
    def test_onnx_inference_not_implemented(self, mock_session_class, tmp_path):
        """Test ONNX inference raises NotImplementedError."""
        model_path = tmp_path / "yolov10.onnx"
        model_path.touch()

        mock_session_class.return_value = MagicMock()

        detector = YOLODetector(str(model_path), device="cpu")
        image = Image.new("RGB", (100, 100))

        # ONNX postprocessing not yet implemented
        with pytest.raises(NotImplementedError, match="ONNX postprocessing not yet implemented"):
            detector.detect(image)


class TestDocLayNetClassMapping:
    """Test DocLayNet class ID to ClassLabelEnum mapping."""

    def test_all_classes_mapped(self):
        """Test all 11 DocLayNet classes are mapped."""
        assert len(DOCLAYNET_CLASS_MAPPING) == 11

        expected_mappings = {
            0: ClassLabelEnum.CAPTION,
            1: ClassLabelEnum.FOOTNOTE,
            2: ClassLabelEnum.FORMULA,
            3: ClassLabelEnum.LIST_ITEM,
            4: ClassLabelEnum.PAGE_FOOTER,
            5: ClassLabelEnum.PAGE_HEADER,
            6: ClassLabelEnum.PICTURE,
            7: ClassLabelEnum.SECTION_HEADER,
            8: ClassLabelEnum.TABLE,
            9: ClassLabelEnum.TEXT,
            10: ClassLabelEnum.TITLE,
        }

        assert DOCLAYNET_CLASS_MAPPING == expected_mappings

    def test_mapping_consistency_with_enum(self):
        """Test mapping values match ClassLabelEnum values."""
        for class_id, class_label in DOCLAYNET_CLASS_MAPPING.items():
            assert isinstance(class_label, ClassLabelEnum)
            assert class_label.value in [
                "caption", "footnote", "formula", "list_item",
                "page_footer", "page_header", "picture", "section_header",
                "table", "text", "title"
            ]


class TestYOLODetectorRepr:
    """Test YOLODetector string representation."""

    @patch("ultralytics.YOLO")
    @patch("torch.cuda")
    def test_repr_pytorch(self, mock_cuda, mock_yolo, tmp_path):
        """Test __repr__ for PyTorch detector."""
        model_path = tmp_path / "yolov10.pt"
        model_path.touch()

        # Mock CUDA availability and YOLO model
        mock_cuda.is_available.return_value = True
        mock_yolo.return_value = MagicMock()

        detector = YOLODetector(str(model_path), device="cuda", input_size=(1024, 1024))
        repr_str = repr(detector)

        assert "YOLODetector" in repr_str
        assert "model_type=pytorch" in repr_str
        assert "device=cuda" in repr_str
        assert "input_size=(1024, 1024)" in repr_str

    @patch("onnxruntime.InferenceSession")
    def test_repr_onnx(self, mock_session_class, tmp_path):
        """Test __repr__ for ONNX detector."""
        model_path = tmp_path / "yolov10.onnx"
        model_path.touch()

        mock_session_class.return_value = MagicMock()

        detector = YOLODetector(str(model_path), device="cpu")
        repr_str = repr(detector)

        assert "model_type=onnx" in repr_str
        assert "device=cpu" in repr_str
