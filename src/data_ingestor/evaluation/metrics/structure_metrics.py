"""
Structure and reading order metrics.

Implements metrics for evaluating document structure preservation:
- Section F1: Heading detection and hierarchy
- Reading order F1: Correct sequence of elements
- Kendall tau: Rank correlation for element ordering
"""

from typing import List, Tuple


def calculate_section_f1(
    predicted_sections: List[Tuple[str, int]],
    ground_truth_sections: List[Tuple[str, int]],
) -> float:
    """
    Calculate Section F1 score.

    Measures how well section headings are detected and their hierarchy preserved.

    Args:
        predicted_sections (List[Tuple[str, int]]): List of (heading_text, level) tuples.
        ground_truth_sections (List[Tuple[str, int]]): List of (heading_text, level) tuples.

    Returns:
        float: F1 score (0.0-1.0, higher = better).

    # TODO(Phase 1.5): Implement fuzzy matching for heading text
    # TODO(Phase 1.5): Consider both text and hierarchy in scoring
    """
    if not ground_truth_sections:
        return 1.0 if not predicted_sections else 0.0

    if not predicted_sections:
        return 0.0

    # Simple exact match implementation (Phase 1)
    # Phase 1.5 will add fuzzy matching and hierarchy weighting

    matches = sum(
        1
        for pred in predicted_sections
        if any(_sections_match(pred, gt) for gt in ground_truth_sections)
    )

    precision = matches / len(predicted_sections) if predicted_sections else 0.0
    recall = matches / len(ground_truth_sections) if ground_truth_sections else 0.0

    if precision + recall == 0:
        return 0.0

    f1 = 2 * precision * recall / (precision + recall)
    return f1


def _sections_match(
    pred: Tuple[str, int],
    gt: Tuple[str, int],
    text_threshold: float = 0.8,
) -> bool:
    """Check if two sections match (text and level)."""
    pred_text, pred_level = pred
    gt_text, gt_level = gt

    # Exact level match required
    if pred_level != gt_level:
        return False

    # Fuzzy text match (simple normalized comparison for now)
    pred_norm = pred_text.lower().strip()
    gt_norm = gt_text.lower().strip()

    # TODO(Phase 1.5): Use proper string similarity (Levenshtein ratio)
    return pred_norm == gt_norm


def calculate_reading_order_f1(
    predicted_order: List[str],
    ground_truth_order: List[str],
) -> float:
    """
    Calculate Reading Order F1 score.

    Measures how well the reading order (sequence) of elements is preserved.

    Args:
        predicted_order (List[str]): List of element IDs in predicted order.
        ground_truth_order (List[str]): List of element IDs in correct order.

    Returns:
        float: F1 score (0.0-1.0, higher = better).

    # TODO(Phase 1.5): Implement longest common subsequence (LCS) approach
    # TODO(Phase 1.5): Consider partial credit for near-miss orderings
    """
    if not ground_truth_order:
        return 1.0 if not predicted_order else 0.0

    if not predicted_order:
        return 0.0

    # Simple implementation: check if elements appear in same relative order
    # Phase 1.5 will use proper sequence alignment

    # Find common elements
    common = set(predicted_order) & set(ground_truth_order)

    if not common:
        return 0.0

    # Extract subsequences of common elements
    pred_subseq = [e for e in predicted_order if e in common]
    gt_subseq = [e for e in ground_truth_order if e in common]

    # Count matching positions (simplified)
    matches = sum(1 for p, g in zip(pred_subseq, gt_subseq) if p == g)

    precision = matches / len(pred_subseq) if pred_subseq else 0.0
    recall = matches / len(gt_subseq) if gt_subseq else 0.0

    if precision + recall == 0:
        return 0.0

    f1 = 2 * precision * recall / (precision + recall)
    return f1


def calculate_kendall_tau(
    predicted_order: List[str],
    ground_truth_order: List[str],
) -> float:
    """
    Calculate Kendall's tau rank correlation coefficient.

    Measures correlation between two rankings. Values range from -1 to 1.

    Args:
        predicted_order (List[str]): List of element IDs in predicted order.
        ground_truth_order (List[str]): List of element IDs in correct order.

    Returns:
        float: Kendall's tau (-1.0 to 1.0, higher = better).

    # TODO(Phase 1.5): Use scipy.stats.kendalltau for proper implementation
    """
    # Find common elements
    common = set(predicted_order) & set(ground_truth_order)

    if len(common) < 2:
        return 0.0

    # Create rankings for common elements
    pred_ranks = {
        elem: i for i, elem in enumerate(predicted_order) if elem in common
    }
    gt_ranks = {
        elem: i
        for i, elem in enumerate(ground_truth_order)
        if elem in common
    }

    # Calculate concordant and discordant pairs
    concordant = 0
    discordant = 0

    common_list = list(common)
    for i in range(len(common_list)):
        for j in range(i + 1, len(common_list)):
            elem1, elem2 = common_list[i], common_list[j]

            # Compare relative orders
            pred_order_correct = (pred_ranks[elem1] < pred_ranks[elem2]) == (
                gt_ranks[elem1] < gt_ranks[elem2]
            )

            if pred_order_correct:
                concordant += 1
            else:
                discordant += 1

    total_pairs = concordant + discordant
    if total_pairs == 0:
        return 0.0

    tau = (concordant - discordant) / total_pairs
    return tau
