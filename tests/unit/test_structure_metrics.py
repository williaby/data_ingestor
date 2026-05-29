"""
Unit tests for structure and reading order metrics.

Tests section F1, reading order F1, and Kendall's tau with comprehensive
coverage of all functions, branches, and edge cases.
"""

from data_ingestor.evaluation.metrics.structure_metrics import (
    calculate_kendall_tau,
    calculate_reading_order_f1,
    calculate_section_f1,
)


class TestCalculateSectionF1:
    """Test section F1 score calculation."""

    def test_perfect_match(self):
        """Test with perfect section matches."""
        sections = [
            ("Introduction", 1),
            ("Methods", 1),
            ("Results", 1),
        ]
        score = calculate_section_f1(sections, sections)
        assert score == 1.0

    def test_partial_match(self):
        """Test with partial section matches."""
        pred = [("Introduction", 1), ("Methods", 1)]
        gt = [("Introduction", 1), ("Results", 1)]
        score = calculate_section_f1(pred, gt)
        # 1 match out of 2 predicted, 1 match out of 2 ground truth
        # Precision = 1/2, Recall = 1/2, F1 = 0.5
        assert score == 0.5

    def test_no_matches(self):
        """Test with no section matches."""
        pred = [("Introduction", 1)]
        gt = [("Results", 1)]
        score = calculate_section_f1(pred, gt)
        assert score == 0.0

    def test_empty_ground_truth(self):
        """Test with empty ground truth."""
        pred = [("Introduction", 1)]
        gt = []
        score = calculate_section_f1(pred, gt)
        assert score == 0.0

    def test_empty_prediction(self):
        """Test with empty prediction."""
        pred = []
        gt = [("Introduction", 1)]
        score = calculate_section_f1(pred, gt)
        assert score == 0.0

    def test_both_empty(self):
        """Test with both empty."""
        score = calculate_section_f1([], [])
        assert score == 1.0

    def test_case_insensitive_matching(self):
        """Test that matching is case insensitive."""
        pred = [("INTRODUCTION", 1)]
        gt = [("introduction", 1)]
        score = calculate_section_f1(pred, gt)
        assert score == 1.0

    def test_whitespace_normalization(self):
        """Test whitespace normalization in section text."""
        pred = [(" Introduction ", 1)]
        gt = [("Introduction", 1)]
        score = calculate_section_f1(pred, gt)
        assert score == 1.0

    def test_different_levels_no_match(self):
        """Test that sections with different levels don't match."""
        pred = [("Introduction", 1)]
        gt = [("Introduction", 2)]
        score = calculate_section_f1(pred, gt)
        assert score == 0.0

    def test_hierarchical_sections(self):
        """Test with hierarchical sections at multiple levels."""
        pred = [
            ("Chapter 1", 1),
            ("Section 1.1", 2),
            ("Section 1.2", 2),
            ("Chapter 2", 1),
        ]
        gt = [
            ("Chapter 1", 1),
            ("Section 1.1", 2),
            ("Chapter 2", 1),
        ]
        score = calculate_section_f1(pred, gt)
        # 3 matches out of 4 predicted, 3 matches out of 3 ground truth
        # Precision = 3/4 = 0.75, Recall = 3/3 = 1.0
        # F1 = 2 * 0.75 * 1.0 / (0.75 + 1.0) = 0.857
        expected = 2 * (3 / 4) * 1.0 / ((3 / 4) + 1.0)
        assert abs(score - expected) < 0.01

    def test_multiple_same_level_sections(self):
        """Test multiple sections at the same level."""
        pred = [("Intro", 1), ("Methods", 1), ("Results", 1)]
        gt = [("Intro", 1), ("Methods", 1), ("Discussion", 1)]
        score = calculate_section_f1(pred, gt)
        # 2 matches, Precision = 2/3, Recall = 2/3, F1 = 2/3
        assert abs(score - 2 / 3) < 0.01


class TestCalculateReadingOrderF1:
    """Test reading order F1 score calculation."""

    def test_perfect_order(self):
        """Test with perfect reading order."""
        order = ["elem1", "elem2", "elem3", "elem4"]
        score = calculate_reading_order_f1(order, order)
        assert score == 1.0

    def test_partial_order_match(self):
        """Test with partial order match."""
        pred = ["elem1", "elem2", "elem3"]
        gt = ["elem1", "elem3", "elem2"]  # elem2 and elem3 swapped
        score = calculate_reading_order_f1(pred, gt)
        # Common elements: elem1, elem2, elem3
        # pred_subseq: [elem1, elem2, elem3]
        # gt_subseq: [elem1, elem3, elem2]
        # Matches: only elem1 at position 0
        assert 0.0 < score < 1.0

    def test_no_common_elements(self):
        """Test with no common elements."""
        pred = ["elem1", "elem2"]
        gt = ["elem3", "elem4"]
        score = calculate_reading_order_f1(pred, gt)
        assert score == 0.0

    def test_empty_ground_truth(self):
        """Test with empty ground truth."""
        pred = ["elem1"]
        gt = []
        score = calculate_reading_order_f1(pred, gt)
        assert score == 0.0

    def test_empty_prediction(self):
        """Test with empty prediction."""
        pred = []
        gt = ["elem1"]
        score = calculate_reading_order_f1(pred, gt)
        assert score == 0.0

    def test_both_empty(self):
        """Test with both empty."""
        score = calculate_reading_order_f1([], [])
        assert score == 1.0

    def test_subset_in_correct_order(self):
        """Test when prediction is subset in correct order."""
        pred = ["elem1", "elem3"]
        gt = ["elem1", "elem2", "elem3", "elem4"]
        score = calculate_reading_order_f1(pred, gt)
        # Common: elem1, elem3
        # Both subsequences: [elem1, elem3]
        # Perfect match on common elements
        assert score == 1.0

    def test_extra_elements_correct_order(self):
        """Test when prediction has extra elements but correct order."""
        pred = ["elem0", "elem1", "elem2", "elem3", "elem5"]
        gt = ["elem1", "elem2", "elem3"]
        score = calculate_reading_order_f1(pred, gt)
        # Common: elem1, elem2, elem3
        # Both have same order for common elements
        assert score == 1.0

    def test_reversed_order(self):
        """Test with completely reversed order."""
        pred = ["elem3", "elem2", "elem1"]
        gt = ["elem1", "elem2", "elem3"]
        score = calculate_reading_order_f1(pred, gt)
        # All common but completely wrong order
        assert 0.0 <= score < 0.5

    def test_partial_reversal(self):
        """Test with partial reversal."""
        pred = ["elem1", "elem3", "elem2", "elem4"]
        gt = ["elem1", "elem2", "elem3", "elem4"]
        score = calculate_reading_order_f1(pred, gt)
        # Most elements present, some out of order
        assert 0.0 < score < 1.0


class TestCalculateKendallTau:
    """Test Kendall's tau rank correlation."""

    def test_perfect_correlation(self):
        """Test with perfect correlation."""
        order = ["a", "b", "c", "d", "e"]
        tau = calculate_kendall_tau(order, order)
        assert tau == 1.0

    def test_perfect_anticorrelation(self):
        """Test with perfect anticorrelation (reversed)."""
        pred = ["a", "b", "c", "d", "e"]
        gt = ["e", "d", "c", "b", "a"]
        tau = calculate_kendall_tau(pred, gt)
        assert tau == -1.0

    def test_no_common_elements(self):
        """Test with no common elements."""
        pred = ["a", "b", "c"]
        gt = ["x", "y", "z"]
        tau = calculate_kendall_tau(pred, gt)
        assert tau == 0.0

    def test_single_common_element(self):
        """Test with single common element."""
        pred = ["a", "b", "c"]
        gt = ["x", "a", "z"]
        tau = calculate_kendall_tau(pred, gt)
        assert tau == 0.0  # Need at least 2 elements for comparison

    def test_partial_agreement(self):
        """Test with partial agreement."""
        pred = ["a", "b", "c", "d"]
        gt = ["a", "c", "b", "d"]
        tau = calculate_kendall_tau(pred, gt)
        # Some concordant, some discordant pairs
        assert -1.0 < tau < 1.0

    def test_subset_perfect_order(self):
        """Test with subset in perfect order."""
        pred = ["a", "b", "x", "c", "d"]
        gt = ["a", "b", "c", "d", "y"]
        tau = calculate_kendall_tau(pred, gt)
        # Common elements: a, b, c, d
        # All in same relative order
        assert tau == 1.0

    def test_two_elements_same_order(self):
        """Test with two elements in same order."""
        pred = ["a", "b"]
        gt = ["a", "b"]
        tau = calculate_kendall_tau(pred, gt)
        assert tau == 1.0

    def test_two_elements_reversed(self):
        """Test with two elements reversed."""
        pred = ["a", "b"]
        gt = ["b", "a"]
        tau = calculate_kendall_tau(pred, gt)
        assert tau == -1.0

    def test_empty_lists(self):
        """Test with empty lists."""
        tau = calculate_kendall_tau([], [])
        assert tau == 0.0

    def test_three_elements_one_swap(self):
        """Test with three elements and one swap."""
        pred = ["a", "b", "c"]
        gt = ["a", "c", "b"]
        tau = calculate_kendall_tau(pred, gt)
        # Pairs: (a,b), (a,c), (b,c)
        # (a,b): both a<b - concordant
        # (a,c): both a<c - concordant
        # (b,c): pred b<c, gt c<b - discordant
        # tau = (2-1)/3 = 1/3
        assert abs(tau - 1 / 3) < 0.01

    def test_alternating_elements(self):
        """Test with alternating common elements."""
        pred = ["a", "x", "b", "y", "c", "z"]
        gt = ["a", "b", "c", "p", "q", "r"]
        tau = calculate_kendall_tau(pred, gt)
        # Common: a, b, c (all in correct order)
        assert tau == 1.0

    def test_complex_ranking(self):
        """Test complex ranking scenario."""
        pred = ["a", "c", "e", "b", "d"]
        gt = ["a", "b", "c", "d", "e"]
        tau = calculate_kendall_tau(pred, gt)
        # Some pairs concordant, some discordant
        assert -1.0 < tau < 1.0
