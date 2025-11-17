"""
Spatial graph construction for reading order prediction.

This module constructs a directed graph from layout detections where nodes
represent layout elements and edges represent spatial relationships.

**Classes:**
- SpatialGraph: Directed graph with spatial relationship edges
- SpatialEdge: Edge connecting two nodes with relationship type
- SpatialRelationship: Enum of spatial relationships (above, below, left, right, etc.)

**Usage:**
    ```python
    from project_b.layout import YOLODetector, Detection
    from project_b.reading_order import SpatialGraph

    # Get layout detections
    detector = YOLODetector("models/yolov10m.pt")
    detections = detector.detect(image)

    # Build spatial graph
    graph = SpatialGraph(detections)

    # Access graph properties
    print(f"Nodes: {len(graph.nodes)}")
    print(f"Edges: {len(graph.edges)}")

    # Get neighbors
    neighbors_below = graph.get_neighbors(node_id=0, relationship="below")
    ```

Schema Version: 1.0.0
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from project_b.layout.detector import Detection


class SpatialRelationship(str, Enum):
    """
    Spatial relationships between layout elements.

    These relationships define how one element is positioned relative to another.
    Used as edge labels in the spatial graph.
    """

    ABOVE = "above"           # Element A is above B (smaller y coordinate)
    BELOW = "below"           # Element A is below B (larger y coordinate)
    LEFT = "left"             # Element A is left of B (smaller x coordinate)
    RIGHT = "right"           # Element A is right of B (larger x coordinate)

    # Diagonal relationships
    ABOVE_LEFT = "above_left"      # Element A is above and to the left of B
    ABOVE_RIGHT = "above_right"    # Element A is above and to the right of B
    BELOW_LEFT = "below_left"      # Element A is below and to the left of B
    BELOW_RIGHT = "below_right"    # Element A is below and to the right of B

    # Multi-column relationships
    SAME_COLUMN = "same_column"    # Elements in same vertical column
    SAME_ROW = "same_row"          # Elements in same horizontal row
    COLUMN_BREAK = "column_break"  # Element starts new column


@dataclass
class SpatialEdge:
    """
    Directed edge in spatial graph.

    Represents a spatial relationship from source node to target node.

    Attributes:
        source_id: Index of source detection
        target_id: Index of target detection
        relationship: Type of spatial relationship
        confidence: Confidence score for this relationship (0.0-1.0)
        distance: Euclidean distance between element centers
    """

    source_id: int
    target_id: int
    relationship: SpatialRelationship
    confidence: float = 1.0
    distance: Optional[float] = None


class SpatialGraph:
    """
    Spatial graph constructed from layout detections.

    Builds a directed graph where:
    - Nodes = layout elements (Detection objects)
    - Edges = spatial relationships (above, below, left, right, etc.)

    The graph is used by ReadingOrderPredictor to determine the sequential
    reading order of elements on a page.

    **Graph Construction:**
    1. Add all detections as nodes
    2. Compute pairwise spatial relationships
    3. Filter edges based on proximity and alignment
    4. Add confidence scores based on spatial cues

    **Example:**
        ```python
        detections = [
            Detection(bbox=[10, 10, 100, 30], class_id=10, ...),  # Title
            Detection(bbox=[10, 50, 100, 20], class_id=9, ...),   # Text
            Detection(bbox=[10, 80, 100, 20], class_id=9, ...),   # Text
        ]

        graph = SpatialGraph(detections)

        # Title is above first text block
        assert graph.has_edge(0, 1, SpatialRelationship.ABOVE)

        # First text block is above second text block
        assert graph.has_edge(1, 2, SpatialRelationship.ABOVE)
        ```
    """

    def __init__(
        self,
        detections: list[Detection],
        max_distance_threshold: float = 500.0,
        alignment_threshold: float = 0.3,
    ):
        """
        Initialize spatial graph from layout detections.

        Args:
            detections: List of layout detections (from YOLODetector)
            max_distance_threshold: Maximum distance to consider relationship (pixels)
            alignment_threshold: Minimum overlap ratio for alignment (0.0-1.0)

        **Algorithm:**
        1. Store detections as nodes with indices
        2. Compute bounding box centers for all nodes
        3. For each pair of nodes:
            a. Compute spatial relationship (above/below/left/right)
            b. Compute distance between centers
            c. Filter by distance threshold
            d. Add edge if relationship is valid
        4. Assign confidence scores based on alignment and distance
        """
        self.detections = detections
        self.max_distance_threshold = max_distance_threshold
        self.alignment_threshold = alignment_threshold

        # Graph structure
        self.nodes: dict[int, Detection] = {}  # node_id -> Detection
        self.edges: list[SpatialEdge] = []     # List of all edges
        self.adjacency_list: dict[int, list[SpatialEdge]] = {}  # node_id -> outgoing edges

        # Build graph
        self._build_graph()

    def _build_graph(self) -> None:
        """
        Build spatial graph from detections.

        Constructs nodes and edges based on spatial relationships.
        """
        # Add nodes
        for idx, detection in enumerate(self.detections):
            self.nodes[idx] = detection
            self.adjacency_list[idx] = []

        # Add edges for all pairwise relationships
        for i in range(len(self.detections)):
            for j in range(len(self.detections)):
                if i == j:
                    continue  # Skip self-loops

                # Compute relationship and add edge if valid
                edge = self._compute_spatial_edge(i, j)
                if edge is not None:
                    self.edges.append(edge)
                    self.adjacency_list[i].append(edge)

    def _compute_spatial_edge(
        self,
        source_id: int,
        target_id: int,
    ) -> Optional[SpatialEdge]:
        """
        Compute spatial relationship edge between two nodes.

        Args:
            source_id: Source node index
            target_id: Target node index

        Returns:
            SpatialEdge if relationship exists, None otherwise

        **Algorithm:**
        1. Extract bounding boxes
        2. Compute centers and dimensions
        3. Determine primary relationship (above/below/left/right)
        4. Compute distance between centers
        5. Filter by distance threshold
        6. Compute confidence score based on alignment
        7. Return edge if confidence > 0
        """
        source_bbox = self.nodes[source_id].bbox
        target_bbox = self.nodes[target_id].bbox

        # Compute centers [x, y, width, height]
        source_center_x = source_bbox[0] + source_bbox[2] / 2
        source_center_y = source_bbox[1] + source_bbox[3] / 2
        target_center_x = target_bbox[0] + target_bbox[2] / 2
        target_center_y = target_bbox[1] + target_bbox[3] / 2

        # Compute distance
        dx = target_center_x - source_center_x
        dy = target_center_y - source_center_y
        distance = (dx**2 + dy**2) ** 0.5

        # Filter by distance threshold
        if distance > self.max_distance_threshold:
            return None

        # Determine primary relationship based on relative positions
        relationship = self._classify_relationship(
            source_bbox, target_bbox, dx, dy
        )

        if relationship is None:
            return None  # No valid relationship

        # Compute confidence based on alignment
        confidence = self._compute_relationship_confidence(
            source_bbox, target_bbox, relationship
        )

        # Only add edge if confidence > 0
        if confidence <= 0:
            return None

        return SpatialEdge(
            source_id=source_id,
            target_id=target_id,
            relationship=relationship,
            confidence=confidence,
            distance=distance,
        )

    def _classify_relationship(
        self,
        source_bbox: list[float],
        target_bbox: list[float],
        dx: float,
        dy: float,
    ) -> Optional[SpatialRelationship]:
        """
        Classify spatial relationship between two bboxes.

        Args:
            source_bbox: Source bbox [x, y, width, height]
            target_bbox: Target bbox [x, y, width, height]
            dx: Horizontal distance (target_center_x - source_center_x)
            dy: Vertical distance (target_center_y - source_center_y)

        Returns:
            SpatialRelationship or None

        **Classification Logic:**
        - Primary axis determined by larger absolute delta (dx vs dy)
        - Vertical: ABOVE if dy < 0, BELOW if dy > 0
        - Horizontal: LEFT if dx < 0, RIGHT if dx > 0
        - Diagonal: Combination of vertical + horizontal
        """
        # Determine primary axis (vertical or horizontal)
        abs_dx = abs(dx)
        abs_dy = abs(dy)

        # Threshold for considering diagonal vs cardinal direction
        diagonal_threshold = 0.5  # If abs_dx and abs_dy within 50%, consider diagonal

        # Pure vertical relationships (dy dominates)
        if abs_dy > abs_dx * (1 + diagonal_threshold):
            if dy < 0:
                return SpatialRelationship.ABOVE
            else:
                return SpatialRelationship.BELOW

        # Pure horizontal relationships (dx dominates)
        elif abs_dx > abs_dy * (1 + diagonal_threshold):
            if dx < 0:
                return SpatialRelationship.LEFT
            else:
                return SpatialRelationship.RIGHT

        # Diagonal relationships (both significant)
        else:
            if dy < 0 and dx < 0:
                return SpatialRelationship.ABOVE_LEFT
            elif dy < 0 and dx > 0:
                return SpatialRelationship.ABOVE_RIGHT
            elif dy > 0 and dx < 0:
                return SpatialRelationship.BELOW_LEFT
            elif dy > 0 and dx > 0:
                return SpatialRelationship.BELOW_RIGHT

        return None

    def _compute_relationship_confidence(
        self,
        source_bbox: list[float],
        target_bbox: list[float],
        relationship: SpatialRelationship,
    ) -> float:
        """
        Compute confidence score for a spatial relationship.

        Args:
            source_bbox: Source bbox [x, y, width, height]
            target_bbox: Target bbox [x, y, width, height]
            relationship: Spatial relationship type

        Returns:
            Confidence score (0.0-1.0)

        **Confidence Factors:**
        - Alignment: Higher confidence if elements are well-aligned
        - Proximity: Higher confidence for closer elements (normalized by distance)
        - Relationship type: Vertical relationships weighted higher (reading flow)
        """
        # Compute alignment based on relationship type
        if relationship in [
            SpatialRelationship.ABOVE,
            SpatialRelationship.BELOW,
        ]:
            # Vertical relationships: measure horizontal alignment
            overlap = self._compute_horizontal_overlap(source_bbox, target_bbox)
            alignment_score = overlap

        elif relationship in [
            SpatialRelationship.LEFT,
            SpatialRelationship.RIGHT,
        ]:
            # Horizontal relationships: measure vertical alignment
            overlap = self._compute_vertical_overlap(source_bbox, target_bbox)
            alignment_score = overlap

        else:
            # Diagonal relationships: lower base confidence
            alignment_score = 0.5

        # Base confidence from alignment
        confidence = alignment_score

        # Boost confidence for vertical relationships (primary reading flow)
        if relationship in [
            SpatialRelationship.ABOVE,
            SpatialRelationship.BELOW,
        ]:
            confidence *= 1.2  # 20% boost for vertical flow

        # Clamp to [0.0, 1.0]
        confidence = max(0.0, min(1.0, confidence))

        return confidence

    def _compute_horizontal_overlap(
        self,
        bbox1: list[float],
        bbox2: list[float],
    ) -> float:
        """
        Compute horizontal overlap ratio between two bboxes.

        Args:
            bbox1: First bbox [x, y, width, height]
            bbox2: Second bbox [x, y, width, height]

        Returns:
            Overlap ratio (0.0-1.0)

        **Algorithm:**
        - Compute intersection of horizontal spans
        - Divide by minimum width
        - Returns 1.0 for perfect alignment, 0.0 for no overlap
        """
        x1_min = bbox1[0]
        x1_max = bbox1[0] + bbox1[2]
        x2_min = bbox2[0]
        x2_max = bbox2[0] + bbox2[2]

        # Compute intersection
        intersection_min = max(x1_min, x2_min)
        intersection_max = min(x1_max, x2_max)
        intersection = max(0, intersection_max - intersection_min)

        # Compute union (minimum of two widths for alignment measure)
        min_width = min(bbox1[2], bbox2[2])

        if min_width == 0:
            return 0.0

        return intersection / min_width

    def _compute_vertical_overlap(
        self,
        bbox1: list[float],
        bbox2: list[float],
    ) -> float:
        """
        Compute vertical overlap ratio between two bboxes.

        Args:
            bbox1: First bbox [x, y, width, height]
            bbox2: Second bbox [x, y, width, height]

        Returns:
            Overlap ratio (0.0-1.0)
        """
        y1_min = bbox1[1]
        y1_max = bbox1[1] + bbox1[3]
        y2_min = bbox2[1]
        y2_max = bbox2[1] + bbox2[3]

        # Compute intersection
        intersection_min = max(y1_min, y2_min)
        intersection_max = min(y1_max, y2_max)
        intersection = max(0, intersection_max - intersection_min)

        # Compute minimum height
        min_height = min(bbox1[3], bbox2[3])

        if min_height == 0:
            return 0.0

        return intersection / min_height

    def has_edge(
        self,
        source_id: int,
        target_id: int,
        relationship: Optional[SpatialRelationship] = None,
    ) -> bool:
        """
        Check if edge exists between two nodes.

        Args:
            source_id: Source node index
            target_id: Target node index
            relationship: Optional specific relationship to check

        Returns:
            True if edge exists, False otherwise
        """
        if source_id not in self.adjacency_list:
            return False

        for edge in self.adjacency_list[source_id]:
            if edge.target_id == target_id:
                if relationship is None or edge.relationship == relationship:
                    return True

        return False

    def get_neighbors(
        self,
        node_id: int,
        relationship: Optional[SpatialRelationship | str] = None,
        min_confidence: float = 0.0,
    ) -> list[int]:
        """
        Get neighbor nodes connected by outgoing edges.

        Args:
            node_id: Node index
            relationship: Optional filter by relationship type
            min_confidence: Minimum confidence threshold

        Returns:
            List of neighbor node indices

        **Example:**
            ```python
            # Get all nodes below this one
            below_nodes = graph.get_neighbors(0, relationship="below")

            # Get high-confidence neighbors
            confident_neighbors = graph.get_neighbors(0, min_confidence=0.7)
            ```
        """
        if node_id not in self.adjacency_list:
            return []

        neighbors = []
        for edge in self.adjacency_list[node_id]:
            # Filter by relationship if specified
            if relationship is not None:
                if isinstance(relationship, str):
                    relationship = SpatialRelationship(relationship)
                if edge.relationship != relationship:
                    continue

            # Filter by confidence
            if edge.confidence < min_confidence:
                continue

            neighbors.append(edge.target_id)

        return neighbors

    def get_outgoing_edges(self, node_id: int) -> list[SpatialEdge]:
        """
        Get all outgoing edges from a node.

        Args:
            node_id: Node index

        Returns:
            List of outgoing edges
        """
        return self.adjacency_list.get(node_id, [])

    def get_incoming_edges(self, node_id: int) -> list[SpatialEdge]:
        """
        Get all incoming edges to a node.

        Args:
            node_id: Node index

        Returns:
            List of incoming edges
        """
        incoming = []
        for edge in self.edges:
            if edge.target_id == node_id:
                incoming.append(edge)
        return incoming

    def __len__(self) -> int:
        """Return number of nodes in graph."""
        return len(self.nodes)

    def __repr__(self) -> str:
        """String representation of graph."""
        return (
            f"SpatialGraph(nodes={len(self.nodes)}, edges={len(self.edges)})"
        )
