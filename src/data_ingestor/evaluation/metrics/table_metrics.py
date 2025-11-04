"""
Table structure metrics.

Implements metrics for evaluating table extraction quality:
- TEDS (Tree Edit Distance Score): Overall table structure similarity
- Cell exact match: Cell-level content accuracy
- Header F1: Header row/column detection
"""

from typing import Dict, List, Optional


def calculate_teds(
    predicted_table: Dict,
    ground_truth_table: Dict,
) -> float:
    """
    Calculate TEDS (Tree Edit Distance Score).

    TEDS measures structural similarity between predicted and ground truth tables
    by computing normalized tree edit distance on the table's HTML structure.

    Args:
        predicted_table: Predicted table structure
        ground_truth_table: Ground truth table structure

    Returns:
        TEDS score (0.0-1.0, higher = better)

    Reference:
        Zhong, X., ShafieiBavani, E., & Jimeno Yepes, A. (2020).
        Image-based table recognition: data, model, and evaluation.

    # TODO(Phase 1.5): Implement proper tree edit distance algorithm
    # TODO(Phase 1.5): Use library like py-apted or custom implementation
    # TODO(Phase 1.5): Handle merged cells, headers, spanning
    """
    if not ground_truth_table:
        return 1.0 if not predicted_table else 0.0

    if not predicted_table:
        return 0.0

    # Simplified implementation for Phase 1
    # Phase 1.5 will use proper tree edit distance

    # Compare basic table dimensions
    pred_rows = len(predicted_table.get("rows", []))
    pred_cols = len(predicted_table.get("cols", []))
    gt_rows = len(ground_truth_table.get("rows", []))
    gt_cols = len(ground_truth_table.get("cols", []))

    # Dimension similarity
    row_sim = 1 - abs(pred_rows - gt_rows) / max(pred_rows, gt_rows, 1)
    col_sim = 1 - abs(pred_cols - gt_cols) / max(pred_cols, gt_cols, 1)

    # Cell content similarity (simplified)
    cell_sim = _calculate_cell_similarity(predicted_table, ground_truth_table)

    # Weighted combination
    teds = 0.3 * row_sim + 0.3 * col_sim + 0.4 * cell_sim

    return teds


def _calculate_cell_similarity(
    predicted: Dict,
    ground_truth: Dict,
) -> float:
    """Calculate cell-level similarity."""
    pred_cells = predicted.get("cells", [])
    gt_cells = ground_truth.get("cells", [])

    if not gt_cells:
        return 1.0 if not pred_cells else 0.0

    if not pred_cells:
        return 0.0

    # Count matching cells (simplified)
    matches = 0
    for pred_cell in pred_cells:
        for gt_cell in gt_cells:
            if _cells_match(pred_cell, gt_cell):
                matches += 1
                break

    similarity = matches / len(gt_cells)
    return similarity


def _cells_match(pred: Dict, gt: Dict, threshold: float = 0.8) -> bool:
    """Check if two cells match."""
    # Compare cell position
    if pred.get("row") != gt.get("row") or pred.get("col") != gt.get("col"):
        return False

    # Compare cell content (normalized)
    pred_text = str(pred.get("text", "")).lower().strip()
    gt_text = str(gt.get("text", "")).lower().strip()

    return pred_text == gt_text


def calculate_cell_exact_match(
    predicted_cells: List[Dict],
    ground_truth_cells: List[Dict],
) -> float:
    """
    Calculate cell exact match accuracy.

    Measures how many cells have exact content and position match.

    Args:
        predicted_cells: List of predicted cells with row, col, text
        ground_truth_cells: List of ground truth cells

    Returns:
        Accuracy score (0.0-1.0, higher = better)
    """
    if not ground_truth_cells:
        return 1.0 if not predicted_cells else 0.0

    if not predicted_cells:
        return 0.0

    # Create lookup dict for predicted cells
    pred_dict = {
        (cell.get("row"), cell.get("col")): cell.get("text", "")
        for cell in predicted_cells
    }

    # Count exact matches
    matches = 0
    for gt_cell in ground_truth_cells:
        row = gt_cell.get("row")
        col = gt_cell.get("col")
        gt_text = gt_cell.get("text", "").strip()

        pred_text = pred_dict.get((row, col), "").strip()

        if pred_text == gt_text:
            matches += 1

    accuracy = matches / len(ground_truth_cells)
    return accuracy


def calculate_header_f1(
    predicted_headers: List[Dict],
    ground_truth_headers: List[Dict],
) -> float:
    """
    Calculate Header F1 score.

    Measures how well header rows/columns are detected.

    Args:
        predicted_headers: List of predicted header cells
        ground_truth_headers: List of ground truth header cells

    Returns:
        F1 score (0.0-1.0, higher = better)
    """
    if not ground_truth_headers:
        return 1.0 if not predicted_headers else 0.0

    if not predicted_headers:
        return 0.0

    # Create sets of header positions
    pred_positions = {
        (h.get("row"), h.get("col")) for h in predicted_headers
    }
    gt_positions = {(h.get("row"), h.get("col")) for h in ground_truth_headers}

    # Calculate true positives, false positives, false negatives
    tp = len(pred_positions & gt_positions)
    fp = len(pred_positions - gt_positions)
    fn = len(gt_positions - pred_positions)

    if tp == 0:
        return 0.0

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    if precision + recall == 0:
        return 0.0

    f1 = 2 * precision * recall / (precision + recall)
    return f1
