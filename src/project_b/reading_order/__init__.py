"""
Reading order prediction module.

This module provides spatial graph construction and reading order prediction
for document layout elements.

**Key Components:**
- SpatialGraph: Directed graph with spatial relationships
- ReadingOrderPredictor: Predict sequential reading order
- ReadingOrderAlgorithm: Available prediction algorithms
- SpatialRelationship: Spatial relationship types

**Usage Example:**
    ```python
    from project_b.layout import YOLODetector
    from project_b.reading_order import (
        SpatialGraph,
        ReadingOrderPredictor,
        ReadingOrderAlgorithm,
    )

    # Get layout detections
    detector = YOLODetector("models/yolov10m.pt")
    detections = detector.detect(image)

    # Build spatial graph
    graph = SpatialGraph(detections)

    # Predict reading order
    predictor = ReadingOrderPredictor(algorithm="column_aware")
    result = predictor.predict(graph)

    # Reorder detections
    ordered_detections = [detections[idx] for idx in result.reading_order]
    ```

Schema Version: 1.0.0
"""

from project_b.reading_order.graph import (
    SpatialEdge,
    SpatialGraph,
    SpatialRelationship,
)
from project_b.reading_order.predictor import (
    ReadingOrderAlgorithm,
    ReadingOrderPredictor,
    ReadingOrderResult,
)

__all__ = [
    # Graph
    "SpatialGraph",
    "SpatialEdge",
    "SpatialRelationship",
    # Predictor
    "ReadingOrderPredictor",
    "ReadingOrderAlgorithm",
    "ReadingOrderResult",
]
