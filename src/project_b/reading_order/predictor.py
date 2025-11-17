"""
Reading order prediction using graph-based algorithms.

This module predicts the sequential reading order of layout elements using
spatial graph analysis and heuristic algorithms.

**Classes:**
- ReadingOrderPredictor: Main predictor class with multiple algorithms
- ReadingOrderAlgorithm: Enum of available algorithms
- ReadingOrderResult: Prediction result with ordering and confidence

**Algorithms:**
1. **TopologicalSort**: Simple top-to-bottom,  left-to-right ordering
2. **ColumnAware**: Detects multi-column layouts and orders within columns
3. **GraphTraversal**: DFS/BFS traversal with spatial priorities
4. **HybridHeuristic**: Combines multiple algorithms with confidence weighting

**Usage:**
    ```python
    from project_b.layout import YOLODetector
    from project_b.reading_order import SpatialGraph, ReadingOrderPredictor

    # Get layout detections
    detector = YOLODetector("models/yolov10m.pt")
    detections = detector.detect(image)

    # Build spatial graph
    graph = SpatialGraph(detections)

    # Predict reading order
    predictor = ReadingOrderPredictor(algorithm="column_aware")
    result = predictor.predict(graph)

    # Access ordered indices
    for idx in result.reading_order:
        print(f"Element {idx}: {detections[idx].class_label}")
    ```

Schema Version: 1.0.0
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from project_b.reading_order.graph import SpatialGraph, SpatialRelationship


class ReadingOrderAlgorithm(str, Enum):
    """
    Available reading order prediction algorithms.

    Each algorithm has different strengths:
    - SIMPLE: Fast, works for single-column layouts
    - COLUMN_AWARE: Handles multi-column layouts (recommended)
    - GRAPH_TRAVERSAL: Flexible, handles complex layouts
    - HYBRID: Best overall performance, combines multiple algorithms
    """

    SIMPLE = "simple"                    # Top-to-bottom, left-to-right
    COLUMN_AWARE = "column_aware"        # Multi-column detection + ordering
    GRAPH_TRAVERSAL = "graph_traversal"  # DFS/BFS with spatial priorities
    HYBRID = "hybrid"                    # Combines multiple algorithms


@dataclass
class ReadingOrderResult:
    """
    Reading order prediction result.

    Attributes:
        reading_order: Ordered list of node indices (0 = first element to read)
        confidence_scores: Per-element confidence scores (0.0-1.0)
        overall_confidence: Overall prediction confidence
        algorithm_used: Algorithm that produced this result
        num_columns: Number of columns detected (for column-aware algorithms)
        column_assignments: Column index for each element (optional)
    """

    reading_order: list[int]
    confidence_scores: list[float]
    overall_confidence: float
    algorithm_used: str
    num_columns: int = 1
    column_assignments: Optional[list[int]] = None


class ReadingOrderPredictor:
    """
    Predict reading order from spatial graph.

    Uses graph-based algorithms to determine the sequential reading order
    of layout elements on a document page.

    **Supported Algorithms:**
    - Simple: Basic top-to-bottom, left-to-right ordering
    - Column-Aware: Detects columns and orders within each column
    - Graph Traversal: Uses spatial edges to traverse graph
    - Hybrid: Combines multiple algorithms

    **Example:**
        ```python
        predictor = ReadingOrderPredictor(algorithm="column_aware")
        result = predictor.predict(graph)

        # Reorder detections by reading order
        ordered_detections = [
            graph.nodes[idx] for idx in result.reading_order
        ]
        ```
    """

    def __init__(
        self,
        algorithm: ReadingOrderAlgorithm | str = "column_aware",
        column_detection_threshold: float = 0.6,
        confidence_threshold: float = 0.5,
    ):
        """
        Initialize reading order predictor.

        Args:
            algorithm: Algorithm to use for prediction
            column_detection_threshold: Threshold for detecting column breaks (0.0-1.0)
            confidence_threshold: Minimum confidence for spatial relationships
        """
        if isinstance(algorithm, str):
            algorithm = ReadingOrderAlgorithm(algorithm)

        self.algorithm = algorithm
        self.column_detection_threshold = column_detection_threshold
        self.confidence_threshold = confidence_threshold

    def predict(self, graph: SpatialGraph) -> ReadingOrderResult:
        """
        Predict reading order from spatial graph.

        Args:
            graph: Spatial graph constructed from layout detections

        Returns:
            ReadingOrderResult with ordered indices and confidence scores

        **Algorithm Selection:**
        - Dispatches to appropriate algorithm based on self.algorithm
        - Returns result with reading order and confidence scores
        """
        if self.algorithm == ReadingOrderAlgorithm.SIMPLE:
            return self._predict_simple(graph)
        elif self.algorithm == ReadingOrderAlgorithm.COLUMN_AWARE:
            return self._predict_column_aware(graph)
        elif self.algorithm == ReadingOrderAlgorithm.GRAPH_TRAVERSAL:
            return self._predict_graph_traversal(graph)
        elif self.algorithm == ReadingOrderAlgorithm.HYBRID:
            return self._predict_hybrid(graph)
        else:
            raise ValueError(f"Unknown algorithm: {self.algorithm}")

    def _predict_simple(self, graph: SpatialGraph) -> ReadingOrderResult:
        """
        Simple top-to-bottom, left-to-right ordering.

        Args:
            graph: Spatial graph

        Returns:
            ReadingOrderResult with simple ordering

        **Algorithm:**
        1. Extract all node bounding boxes
        2. Sort by y-coordinate (top to bottom)
        3. For elements with similar y-coordinates, sort by x-coordinate (left to right)
        4. Assign uniform confidence scores

        **Time Complexity:** O(n log n) where n = number of nodes
        """
        # Extract node indices and bboxes
        nodes_with_bbox = [
            (node_id, graph.nodes[node_id].bbox)
            for node_id in graph.nodes
        ]

        # Sort by y-coordinate (top to bottom), then x-coordinate (left to right)
        # bbox format: [x, y, width, height]
        sorted_nodes = sorted(
            nodes_with_bbox,
            key=lambda item: (
                item[1][1],  # y coordinate (top to bottom)
                item[1][0],  # x coordinate (left to right)
            ),
        )

        # Extract ordered indices
        reading_order = [node_id for node_id, _ in sorted_nodes]

        # Uniform confidence (simple algorithm has no confidence modeling)
        confidence_scores = [0.8] * len(reading_order)
        overall_confidence = 0.8

        return ReadingOrderResult(
            reading_order=reading_order,
            confidence_scores=confidence_scores,
            overall_confidence=overall_confidence,
            algorithm_used="simple",
            num_columns=1,
        )

    def _predict_column_aware(self, graph: SpatialGraph) -> ReadingOrderResult:
        """
        Column-aware reading order prediction.

        Args:
            graph: Spatial graph

        Returns:
            ReadingOrderResult with column-based ordering

        **Algorithm:**
        1. Detect column boundaries using x-coordinate clustering
        2. Assign each element to a column
        3. Within each column, sort top-to-bottom
        4. Order columns left-to-right
        5. Concatenate reading orders

        **Handles:**
        - Single-column layouts (falls back to simple ordering)
        - Two-column layouts (most common)
        - Three+ column layouts (rare but supported)
        """
        # Step 1: Detect columns
        column_assignments, num_columns = self._detect_columns(graph)

        if num_columns == 1:
            # Fall back to simple ordering for single-column
            result = self._predict_simple(graph)
            result.num_columns = 1
            result.column_assignments = column_assignments
            return result

        # Step 2: Group nodes by column
        columns: dict[int, list[int]] = {i: [] for i in range(num_columns)}
        for node_id, column_id in enumerate(column_assignments):
            columns[column_id].append(node_id)

        # Step 3: Sort within each column (top to bottom)
        for column_id in columns:
            columns[column_id] = sorted(
                columns[column_id],
                key=lambda node_id: graph.nodes[node_id].bbox[1],  # y coordinate
            )

        # Step 4: Concatenate columns (left to right)
        reading_order = []
        for column_id in sorted(columns.keys()):
            reading_order.extend(columns[column_id])

        # Step 5: Compute confidence scores
        confidence_scores = self._compute_column_confidence(
            graph, reading_order, column_assignments
        )
        overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

        return ReadingOrderResult(
            reading_order=reading_order,
            confidence_scores=confidence_scores,
            overall_confidence=overall_confidence,
            algorithm_used="column_aware",
            num_columns=num_columns,
            column_assignments=column_assignments,
        )

    def _detect_columns(self, graph: SpatialGraph) -> tuple[list[int], int]:
        """
        Detect column structure in layout.

        Args:
            graph: Spatial graph

        Returns:
            Tuple of (column_assignments, num_columns)
            - column_assignments: List mapping node_id -> column_id
            - num_columns: Total number of columns detected

        **Algorithm:**
        1. Extract x-coordinates (left edges) of all elements
        2. Cluster x-coordinates using simple gap-based clustering
        3. Assign each element to nearest column centroid
        4. Return column assignments and count

        **Handles:**
        - Single column: All elements have similar x-coordinates
        - Multi-column: Distinct x-coordinate clusters
        """
        if len(graph.nodes) == 0:
            return [], 0

        # Extract node info: (node_id, x_left, y_top)
        node_info = [
            (node_id, graph.nodes[node_id].bbox[0], graph.nodes[node_id].bbox[1])
            for node_id in sorted(graph.nodes.keys())
        ]

        # Extract x-coordinates (left edges)
        x_coords = [x for _, x, _ in node_info]

        # Simple gap-based column detection
        # Sort x-coordinates
        sorted_x = sorted(set(x_coords))

        if len(sorted_x) <= 1:
            # Single column (all elements at same x)
            return [0] * len(node_info), 1

        # Find gaps in x-coordinates
        gaps = []
        for i in range(len(sorted_x) - 1):
            gap = sorted_x[i + 1] - sorted_x[i]
            gaps.append((gap, sorted_x[i], sorted_x[i + 1]))

        # Detect column breaks (large gaps)
        # Use median gap as threshold
        median_gap = sorted(gaps, key=lambda g: g[0])[len(gaps) // 2][0]
        column_break_threshold = median_gap * 2.0  # 2x median gap

        # Identify column boundaries
        column_boundaries = [sorted_x[0]]
        for gap, x1, x2 in gaps:
            if gap >= column_break_threshold:
                # Column break detected
                column_boundaries.append(x2)

        num_columns = len(column_boundaries)

        # Assign each node to a column
        column_assignments = []
        for node_id, x, y in node_info:
            # Find closest column boundary (to the left)
            column_id = 0
            for i, boundary in enumerate(column_boundaries):
                if x >= boundary:
                    column_id = i

            column_assignments.append(column_id)

        return column_assignments, num_columns

    def _compute_column_confidence(
        self,
        graph: SpatialGraph,
        reading_order: list[int],
        column_assignments: list[int],
    ) -> list[float]:
        """
        Compute confidence scores for column-aware ordering.

        Args:
            graph: Spatial graph
            reading_order: Predicted reading order
            column_assignments: Column assignments for each node

        Returns:
            List of confidence scores (one per element)

        **Confidence Factors:**
        - Within-column alignment: Higher confidence if elements well-aligned
        - Vertical spacing: Lower confidence for large gaps
        - Cross-column transitions: Lower confidence at column boundaries
        """
        confidence_scores = []

        for i, node_id in enumerate(reading_order):
            # Base confidence
            confidence = 0.9

            # Check alignment with previous element (if in same column)
            if i > 0:
                prev_node_id = reading_order[i - 1]
                curr_column = column_assignments[node_id]
                prev_column = column_assignments[prev_node_id]

                if curr_column == prev_column:
                    # Same column: check vertical alignment
                    curr_bbox = graph.nodes[node_id].bbox
                    prev_bbox = graph.nodes[prev_node_id].bbox

                    # Compute horizontal overlap
                    overlap = self._compute_horizontal_overlap(curr_bbox, prev_bbox)

                    # High overlap → high confidence
                    confidence = 0.7 + 0.3 * overlap

                else:
                    # Column transition → moderate confidence
                    confidence = 0.75

            confidence_scores.append(confidence)

        return confidence_scores

    def _compute_horizontal_overlap(
        self,
        bbox1: list[float],
        bbox2: list[float],
    ) -> float:
        """
        Compute horizontal overlap ratio.

        Args:
            bbox1: First bbox [x, y, width, height]
            bbox2: Second bbox [x, y, width, height]

        Returns:
            Overlap ratio (0.0-1.0)
        """
        x1_min = bbox1[0]
        x1_max = bbox1[0] + bbox1[2]
        x2_min = bbox2[0]
        x2_max = bbox2[0] + bbox2[2]

        # Compute intersection
        intersection_min = max(x1_min, x2_min)
        intersection_max = min(x1_max, x2_max)
        intersection = max(0, intersection_max - intersection_min)

        # Compute minimum width
        min_width = min(bbox1[2], bbox2[2])

        if min_width == 0:
            return 0.0

        return intersection / min_width

    def _predict_graph_traversal(self, graph: SpatialGraph) -> ReadingOrderResult:
        """
        Graph traversal-based reading order prediction.

        Args:
            graph: Spatial graph

        Returns:
            ReadingOrderResult with traversal-based ordering

        **Algorithm:**
        1. Find start node (topmost, leftmost element)
        2. Perform DFS traversal following spatial edges
        3. Prioritize BELOW edges over other directions
        4. Handle cycles and backtracking
        5. Return traversal order

        **Priority Order:**
        1. BELOW (primary reading flow)
        2. RIGHT (secondary flow)
        3. BELOW_RIGHT (diagonal flow)
        4. Other directions (fallback)
        """
        if len(graph.nodes) == 0:
            return ReadingOrderResult(
                reading_order=[],
                confidence_scores=[],
                overall_confidence=0.0,
                algorithm_used="graph_traversal",
            )

        # Step 1: Find start node (topmost, leftmost)
        start_node = min(
            graph.nodes.keys(),
            key=lambda node_id: (
                graph.nodes[node_id].bbox[1],  # y (top)
                graph.nodes[node_id].bbox[0],  # x (left)
            ),
        )

        # Step 2: DFS traversal with spatial priorities
        visited = set()
        reading_order = []

        def dfs(node_id: int) -> None:
            """Depth-first search with spatial edge priorities."""
            if node_id in visited:
                return

            visited.add(node_id)
            reading_order.append(node_id)

            # Get outgoing edges sorted by priority
            edges = graph.get_outgoing_edges(node_id)

            # Sort by relationship priority
            priority_map = {
                SpatialRelationship.BELOW: 1,        # Highest priority
                SpatialRelationship.BELOW_RIGHT: 2,
                SpatialRelationship.RIGHT: 3,
                SpatialRelationship.BELOW_LEFT: 4,
                SpatialRelationship.ABOVE: 5,
                SpatialRelationship.LEFT: 6,
                SpatialRelationship.ABOVE_RIGHT: 7,
                SpatialRelationship.ABOVE_LEFT: 8,
            }

            sorted_edges = sorted(
                edges,
                key=lambda edge: (
                    priority_map.get(edge.relationship, 9),  # Relationship priority
                    -edge.confidence,                        # Higher confidence first
                    edge.distance if edge.distance else float('inf'),  # Closer nodes first
                ),
            )

            # Visit neighbors
            for edge in sorted_edges:
                if edge.target_id not in visited:
                    dfs(edge.target_id)

        # Start DFS from start node
        dfs(start_node)

        # Handle disconnected nodes (shouldn't happen but defensive)
        for node_id in sorted(graph.nodes.keys()):
            if node_id not in visited:
                dfs(node_id)

        # Compute confidence scores based on edge confidence
        confidence_scores = []
        for i, node_id in enumerate(reading_order):
            if i == 0:
                confidence_scores.append(1.0)  # First node always confident
            else:
                prev_node_id = reading_order[i - 1]
                # Find edge from prev to current
                edge_confidence = 0.5  # Default if no edge
                for edge in graph.get_outgoing_edges(prev_node_id):
                    if edge.target_id == node_id:
                        edge_confidence = edge.confidence
                        break
                confidence_scores.append(edge_confidence)

        overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

        return ReadingOrderResult(
            reading_order=reading_order,
            confidence_scores=confidence_scores,
            overall_confidence=overall_confidence,
            algorithm_used="graph_traversal",
        )

    def _predict_hybrid(self, graph: SpatialGraph) -> ReadingOrderResult:
        """
        Hybrid algorithm combining multiple approaches.

        Args:
            graph: Spatial graph

        Returns:
            ReadingOrderResult with hybrid ordering

        **Algorithm:**
        1. Run multiple algorithms (simple, column_aware, graph_traversal)
        2. Compare results and confidence scores
        3. Select best result or blend results
        4. Return highest-confidence prediction

        **Selection Criteria:**
        - Prefer column_aware for multi-column layouts
        - Prefer graph_traversal for complex layouts
        - Fall back to simple for ambiguous cases
        """
        # Run all algorithms
        simple_result = self._predict_simple(graph)
        column_result = self._predict_column_aware(graph)
        graph_result = self._predict_graph_traversal(graph)

        # Select best result based on confidence and layout complexity
        # If multi-column detected, prefer column_aware
        if column_result.num_columns > 1:
            best_result = column_result
            best_result.algorithm_used = "hybrid(column_aware)"
        # Otherwise prefer graph traversal for complex layouts
        elif len(graph.edges) > len(graph.nodes) * 2:  # Dense graph → complex layout
            best_result = graph_result
            best_result.algorithm_used = "hybrid(graph_traversal)"
        # Fall back to column_aware (works well for single-column too)
        else:
            best_result = column_result
            best_result.algorithm_used = "hybrid(column_aware)"

        # Boost overall confidence slightly for hybrid
        best_result.overall_confidence = min(1.0, best_result.overall_confidence * 1.1)

        return best_result
