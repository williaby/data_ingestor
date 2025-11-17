"""
YOLOv10-doc layout detector for Project B.

This module implements layout detection using YOLOv10-doc trained on DocLayNet
to identify 11 structural document elements.

**Architecture Decision**: ADR-0005 - YOLOv10-doc for Layout Detection
- Model: YOLOv10m trained on DocLayNet
- Performance: mAP@0.50 = 0.84, 50-100ms inference on GPU
- Classes: 11 DocLayNet classes (caption, footnote, formula, list_item,
  page_footer, page_header, picture, section_header, table, text, title)

**Usage:**
    ```python
    from project_b.layout.detector import YOLODetector
    from PIL import Image

    detector = YOLODetector(model_path="models/yolov10m_doclaynet.pt")
    image = Image.open("document_page.png")
    detections = detector.detect(image, confidence_threshold=0.3)
    ```

Schema Version: 1.0.0
"""

from pathlib import Path
from typing import Optional, Union

import numpy as np
from PIL import Image
from pydantic import BaseModel, Field

from project_b.schemas.ocr_document import ClassLabelEnum


# DocLayNet class label mapping (YOLOv10-doc → ClassLabelEnum)
DOCLAYNET_CLASS_MAPPING = {
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


class Detection(BaseModel):
    """
    Single layout detection with bounding box and class label.

    **COCO Format Bbox**: [x, y, width, height] in pixels
    - x, y: top-left corner coordinates
    - width, height: box dimensions
    """

    bbox: list[float] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="COCO format bbox [x, y, width, height]",
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    class_id: int = Field(..., ge=0, le=10, description="DocLayNet class ID (0-10)")
    class_label: ClassLabelEnum = Field(..., description="DocLayNet class label")


class YOLODetector:
    """
    YOLOv10-doc layout detector for document page analysis.

    This detector identifies 11 structural elements using YOLOv10m trained on
    the DocLayNet dataset (80k+ documents with layout annotations).

    **Model Support:**
    - ONNX Runtime (recommended for production deployment)
    - PyTorch (for development and fine-tuning)

    **Performance Targets** (ADR-0005):
    - mAP@0.50 ≥ 0.84 on DocLayNet validation
    - Inference: 50-100ms/page on GPU, <300ms on CPU
    - Input: 640x640 or 1024x1024 (model-dependent)

    **Attributes:**
        model_path: Path to YOLOv10 model (.pt or .onnx)
        device: Device for inference ("cuda" or "cpu")
        model: Loaded model instance (PyTorch or ONNX)
        model_type: "pytorch" or "onnx"
        input_size: Model input size (width, height)

    **Example:**
        ```python
        detector = YOLODetector("models/yolov10m_doclaynet.pt", device="cuda")
        detections = detector.detect(image, confidence_threshold=0.3)
        print(f"Found {len(detections)} layout elements")
        ```
    """

    def __init__(
        self,
        model_path: Union[str, Path],
        device: str = "cuda",
        input_size: tuple[int, int] = (1024, 1024),
    ):
        """
        Initialize YOLOv10 layout detector.

        Args:
            model_path: Path to YOLOv10 model file (.pt or .onnx)
            device: Device for inference ("cuda" or "cpu")
            input_size: Model input size (width, height). Common: (640, 640) or (1024, 1024)

        Raises:
            FileNotFoundError: If model_path does not exist
            ValueError: If model_path has unsupported extension
            ImportError: If required dependencies (torch or onnxruntime) not installed
        """
        self.model_path = Path(model_path)
        self.device = device
        self.input_size = input_size

        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")

        # Determine model type from extension
        if self.model_path.suffix == ".pt":
            self.model_type = "pytorch"
            self._load_pytorch_model()
        elif self.model_path.suffix == ".onnx":
            self.model_type = "onnx"
            self._load_onnx_model()
        else:
            raise ValueError(
                f"Unsupported model format: {self.model_path.suffix}. "
                f"Supported: .pt (PyTorch), .onnx (ONNX)"
            )

    def _load_pytorch_model(self) -> None:
        """
        Load YOLOv10 PyTorch model.

        Raises:
            ImportError: If torch or ultralytics not installed
        """
        try:
            from ultralytics import YOLO
        except ImportError as e:
            raise ImportError(
                "PyTorch/Ultralytics not installed. "
                "Install with: pip install ultralytics torch"
            ) from e

        # Load YOLO model
        self.model = YOLO(str(self.model_path))

        # Move to specified device
        if self.device == "cuda":
            import torch

            if not torch.cuda.is_available():
                raise RuntimeError(
                    "CUDA requested but not available. Set device='cpu' or install CUDA."
                )
            self.model.to("cuda")
        else:
            self.model.to("cpu")

    def _load_onnx_model(self) -> None:
        """
        Load YOLOv10 ONNX model.

        Raises:
            ImportError: If onnxruntime not installed
        """
        try:
            import onnxruntime as ort
        except ImportError as e:
            raise ImportError(
                "ONNX Runtime not installed. "
                "Install with: pip install onnxruntime-gpu (or onnxruntime for CPU)"
            ) from e

        # Configure ONNX Runtime session
        providers = []
        if self.device == "cuda":
            providers.append("CUDAExecutionProvider")
        providers.append("CPUExecutionProvider")

        # Create ONNX session
        self.model = ort.InferenceSession(
            str(self.model_path), providers=providers
        )

    def detect(
        self,
        image: Union[Image.Image, np.ndarray, str, Path],
        confidence_threshold: float = 0.3,
        iou_threshold: float = 0.45,
    ) -> list[Detection]:
        """
        Detect layout elements in document page image.

        Args:
            image: Input image (PIL Image, numpy array, or file path)
            confidence_threshold: Minimum confidence for detections (0.0-1.0)
            iou_threshold: IoU threshold for NMS (0.0-1.0)

        Returns:
            List of Detection objects with bbox, confidence, class_id, class_label

        Raises:
            ValueError: If image is invalid or confidence_threshold out of range

        **Performance:**
        - GPU: 50-100ms for 1024x1024 input
        - CPU: 150-300ms for 1024x1024 input

        **Example:**
            ```python
            from PIL import Image
            detector = YOLODetector("yolov10m.pt")
            image = Image.open("page.png")
            detections = detector.detect(image, confidence_threshold=0.3)

            for det in detections:
                print(f"{det.class_label.value}: {det.confidence:.2f}")
            ```
        """
        # Validate threshold
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError(
                f"confidence_threshold must be in [0.0, 1.0], got {confidence_threshold}"
            )
        if not 0.0 <= iou_threshold <= 1.0:
            raise ValueError(
                f"iou_threshold must be in [0.0, 1.0], got {iou_threshold}"
            )

        # Load image if path provided
        if isinstance(image, (str, Path)):
            image = Image.open(image).convert("RGB")
        elif isinstance(image, np.ndarray):
            image = Image.fromarray(image).convert("RGB")
        elif not isinstance(image, Image.Image):
            raise ValueError(
                f"image must be PIL Image, numpy array, or path. Got {type(image)}"
            )

        # Run inference based on model type
        if self.model_type == "pytorch":
            return self._detect_pytorch(image, confidence_threshold, iou_threshold)
        else:
            return self._detect_onnx(image, confidence_threshold, iou_threshold)

    def _detect_pytorch(
        self,
        image: Image.Image,
        confidence_threshold: float,
        iou_threshold: float,
    ) -> list[Detection]:
        """
        Run inference using PyTorch/Ultralytics model.

        Args:
            image: PIL Image (RGB)
            confidence_threshold: Min confidence for detections
            iou_threshold: IoU threshold for NMS

        Returns:
            List of Detection objects
        """
        # Run YOLO inference
        results = self.model.predict(
            image,
            conf=confidence_threshold,
            iou=iou_threshold,
            imgsz=self.input_size[0],  # Use square input
            verbose=False,
        )

        # Extract detections from results
        detections = []
        if len(results) > 0 and results[0].boxes is not None:
            boxes = results[0].boxes

            # Convert to COCO format and create Detection objects
            for box in boxes:
                # Extract box coordinates (xyxy format from YOLO)
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

                # Convert to COCO format [x, y, width, height]
                bbox = [float(x1), float(y1), float(x2 - x1), float(y2 - y1)]

                # Extract confidence and class
                confidence = float(box.conf[0])
                class_id = int(box.cls[0])

                # Map class ID to ClassLabelEnum
                if class_id in DOCLAYNET_CLASS_MAPPING:
                    class_label = DOCLAYNET_CLASS_MAPPING[class_id]

                    detections.append(
                        Detection(
                            bbox=bbox,
                            confidence=confidence,
                            class_id=class_id,
                            class_label=class_label,
                        )
                    )

        return detections

    def _detect_onnx(
        self,
        image: Image.Image,
        confidence_threshold: float,
        iou_threshold: float,
    ) -> list[Detection]:
        """
        Run inference using ONNX Runtime.

        Args:
            image: PIL Image (RGB)
            confidence_threshold: Min confidence for detections
            iou_threshold: IoU threshold for NMS

        Returns:
            List of Detection objects

        Note:
            ONNX inference requires manual preprocessing and postprocessing.
            PyTorch model handles this internally via Ultralytics.
        """
        # Preprocess image to model input format
        input_tensor = self._preprocess_image_onnx(image)

        # Run ONNX inference
        input_name = self.model.get_inputs()[0].name
        outputs = self.model.run(None, {input_name: input_tensor})

        # Postprocess ONNX outputs to detections
        detections = self._postprocess_onnx_outputs(
            outputs, image.size, confidence_threshold, iou_threshold
        )

        return detections

    def _preprocess_image_onnx(self, image: Image.Image) -> np.ndarray:
        """
        Preprocess PIL image for ONNX model input.

        Args:
            image: PIL Image (RGB)

        Returns:
            Preprocessed numpy array (1, 3, H, W) in [0, 1] range
        """
        # Resize to model input size
        image_resized = image.resize(self.input_size, Image.Resampling.BILINEAR)

        # Convert to numpy array and normalize
        img_array = np.array(image_resized).astype(np.float32) / 255.0

        # Transpose to (C, H, W) and add batch dimension
        img_array = img_array.transpose(2, 0, 1)[np.newaxis, ...]

        return img_array

    def _postprocess_onnx_outputs(
        self,
        outputs: list[np.ndarray],
        original_size: tuple[int, int],
        confidence_threshold: float,
        iou_threshold: float,
    ) -> list[Detection]:
        """
        Postprocess ONNX model outputs to Detection objects.

        Args:
            outputs: Raw ONNX model outputs
            original_size: Original image size (width, height)
            confidence_threshold: Min confidence for detections
            iou_threshold: IoU threshold for NMS

        Returns:
            List of Detection objects with bboxes scaled to original image size

        Note:
            This is a placeholder implementation. Actual ONNX postprocessing
            depends on the specific YOLOv10 ONNX export format.
        """
        # TODO: Implement ONNX-specific postprocessing
        # This requires understanding the ONNX model output format
        # (typically [batch, num_detections, 5+num_classes])

        raise NotImplementedError(
            "ONNX postprocessing not yet implemented. "
            "Use PyTorch model (.pt) for now, or implement ONNX postprocessing."
        )

    def __repr__(self) -> str:
        """String representation of YOLODetector."""
        return (
            f"YOLODetector(model_type={self.model_type}, "
            f"device={self.device}, "
            f"input_size={self.input_size})"
        )
