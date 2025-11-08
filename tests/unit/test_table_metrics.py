"""
Unit tests for table structure metrics.

Tests TEDS, cell exact match, and header F1 metrics with comprehensive
coverage of all functions, branches, and edge cases.
"""

import pytest

from data_ingestor.evaluation.metrics.table_metrics import (
    calculate_cell_exact_match,
    calculate_header_f1,
    calculate_teds,
)


class TestCalculateTEDS:
    """Test TEDS (Tree Edit Distance Score) calculation."""

    def test_identical_tables(self):
        """Test TEDS with identical tables."""
        table = {
            "rows": [[1, 2, 3]],
            "cols": [[1], [2], [3]],
            "cells": [
                {"row": 0, "col": 0, "text": "A"},
                {"row": 0, "col": 1, "text": "B"},
            ],
        }
        score = calculate_teds(table, table)
        assert score == 1.0

    def test_different_dimensions(self):
        """Test TEDS with different table dimensions."""
        pred = {"rows": [[1, 2]], "cols": [[1], [2]], "cells": []}
        gt = {"rows": [[1, 2, 3]], "cols": [[1], [2], [3]], "cells": []}
        score = calculate_teds(pred, gt)
        # Should penalize dimension mismatch
        assert 0.0 < score < 1.0

    def test_empty_ground_truth(self):
        """Test TEDS with empty ground truth."""
        pred = {"rows": [[1]], "cols": [[1]], "cells": []}
        gt = {}
        score = calculate_teds(pred, gt)
        assert score == 0.0

    def test_empty_prediction(self):
        """Test TEDS with empty prediction."""
        pred = {}
        gt = {"rows": [[1]], "cols": [[1]], "cells": []}
        score = calculate_teds(pred, gt)
        assert score == 0.0

    def test_both_empty(self):
        """Test TEDS with both tables empty."""
        score = calculate_teds({}, {})
        assert score == 1.0

    def test_cell_content_similarity(self):
        """Test TEDS with different cell content."""
        pred = {
            "rows": [[1, 2]],
            "cols": [[1], [2]],
            "cells": [
                {"row": 0, "col": 0, "text": "A"},
                {"row": 0, "col": 1, "text": "B"},
            ],
        }
        gt = {
            "rows": [[1, 2]],
            "cols": [[1], [2]],
            "cells": [
                {"row": 0, "col": 0, "text": "A"},
                {"row": 0, "col": 1, "text": "C"},  # Different content
            ],
        }
        score = calculate_teds(pred, gt)
        # Should be less than 1.0 due to content mismatch
        assert 0.0 < score < 1.0

    def test_missing_cells_in_prediction(self):
        """Test TEDS when prediction has fewer cells."""
        pred = {
            "rows": [[1, 2]],
            "cols": [[1], [2]],
            "cells": [{"row": 0, "col": 0, "text": "A"}],
        }
        gt = {
            "rows": [[1, 2]],
            "cols": [[1], [2]],
            "cells": [
                {"row": 0, "col": 0, "text": "A"},
                {"row": 0, "col": 1, "text": "B"},
            ],
        }
        score = calculate_teds(pred, gt)
        assert 0.0 < score < 1.0

    def test_extra_cells_in_prediction(self):
        """Test TEDS when prediction has extra cells."""
        pred = {
            "rows": [[1, 2]],
            "cols": [[1], [2]],
            "cells": [
                {"row": 0, "col": 0, "text": "A"},
                {"row": 0, "col": 1, "text": "B"},
                {"row": 0, "col": 2, "text": "C"},
            ],
        }
        gt = {
            "rows": [[1, 2]],
            "cols": [[1], [2]],
            "cells": [
                {"row": 0, "col": 0, "text": "A"},
                {"row": 0, "col": 1, "text": "B"},
            ],
        }
        score = calculate_teds(pred, gt)
        # All GT cells match, so cell similarity is 1.0 even with extra predictions
        assert 0.0 < score <= 1.0

    def test_no_rows_or_cols(self):
        """Test TEDS with tables that have no rows/cols keys."""
        pred = {"cells": [{"row": 0, "col": 0, "text": "A"}]}
        gt = {"cells": [{"row": 0, "col": 0, "text": "A"}]}
        score = calculate_teds(pred, gt)
        # Should handle missing keys gracefully
        assert 0.0 <= score <= 1.0


class TestCalculateCellExactMatch:
    """Test cell exact match accuracy."""

    def test_perfect_match(self):
        """Test with perfect cell matches."""
        cells = [
            {"row": 0, "col": 0, "text": "A"},
            {"row": 0, "col": 1, "text": "B"},
            {"row": 1, "col": 0, "text": "C"},
        ]
        score = calculate_cell_exact_match(cells, cells)
        assert score == 1.0

    def test_partial_match(self):
        """Test with partial cell matches."""
        pred = [
            {"row": 0, "col": 0, "text": "A"},
            {"row": 0, "col": 1, "text": "B"},
        ]
        gt = [
            {"row": 0, "col": 0, "text": "A"},
            {"row": 0, "col": 1, "text": "C"},  # Different
        ]
        score = calculate_cell_exact_match(pred, gt)
        assert score == 0.5

    def test_no_matches(self):
        """Test with no cell matches."""
        pred = [{"row": 0, "col": 0, "text": "A"}]
        gt = [{"row": 0, "col": 0, "text": "B"}]
        score = calculate_cell_exact_match(pred, gt)
        assert score == 0.0

    def test_empty_ground_truth(self):
        """Test with empty ground truth."""
        pred = [{"row": 0, "col": 0, "text": "A"}]
        gt = []
        score = calculate_cell_exact_match(pred, gt)
        assert score == 0.0

    def test_empty_prediction(self):
        """Test with empty prediction."""
        pred = []
        gt = [{"row": 0, "col": 0, "text": "A"}]
        score = calculate_cell_exact_match(pred, gt)
        assert score == 0.0

    def test_both_empty(self):
        """Test with both empty."""
        score = calculate_cell_exact_match([], [])
        assert score == 1.0

    def test_whitespace_handling(self):
        """Test that whitespace is handled correctly."""
        pred = [{"row": 0, "col": 0, "text": " A "}]
        gt = [{"row": 0, "col": 0, "text": "A"}]
        score = calculate_cell_exact_match(pred, gt)
        assert score == 1.0

    def test_position_mismatch(self):
        """Test cells with same text but different positions."""
        pred = [{"row": 0, "col": 0, "text": "A"}]
        gt = [{"row": 1, "col": 1, "text": "A"}]
        score = calculate_cell_exact_match(pred, gt)
        assert score == 0.0

    def test_missing_text_field(self):
        """Test cells with missing text field."""
        pred = [{"row": 0, "col": 0}]
        gt = [{"row": 0, "col": 0, "text": ""}]
        score = calculate_cell_exact_match(pred, gt)
        assert score == 1.0  # Both empty text

    def test_multiple_cells_same_content(self):
        """Test multiple cells with same content at different positions."""
        pred = [
            {"row": 0, "col": 0, "text": "A"},
            {"row": 0, "col": 1, "text": "A"},
        ]
        gt = [
            {"row": 0, "col": 0, "text": "A"},
            {"row": 0, "col": 1, "text": "A"},
        ]
        score = calculate_cell_exact_match(pred, gt)
        assert score == 1.0


class TestCalculateHeaderF1:
    """Test header F1 score calculation."""

    def test_perfect_match(self):
        """Test with perfect header matches."""
        headers = [
            {"row": 0, "col": 0},
            {"row": 0, "col": 1},
            {"row": 0, "col": 2},
        ]
        score = calculate_header_f1(headers, headers)
        assert score == 1.0

    def test_partial_match(self):
        """Test with partial header matches."""
        pred = [{"row": 0, "col": 0}, {"row": 0, "col": 1}]
        gt = [{"row": 0, "col": 0}, {"row": 0, "col": 2}]
        score = calculate_header_f1(pred, gt)
        # 1 TP, 1 FP, 1 FN
        # Precision = 1/2, Recall = 1/2, F1 = 0.5
        assert score == 0.5

    def test_no_matches(self):
        """Test with no header matches."""
        pred = [{"row": 0, "col": 0}]
        gt = [{"row": 1, "col": 1}]
        score = calculate_header_f1(pred, gt)
        assert score == 0.0

    def test_empty_ground_truth(self):
        """Test with empty ground truth."""
        pred = [{"row": 0, "col": 0}]
        gt = []
        score = calculate_header_f1(pred, gt)
        assert score == 0.0

    def test_empty_prediction(self):
        """Test with empty prediction."""
        pred = []
        gt = [{"row": 0, "col": 0}]
        score = calculate_header_f1(pred, gt)
        assert score == 0.0

    def test_both_empty(self):
        """Test with both empty."""
        score = calculate_header_f1([], [])
        assert score == 1.0

    def test_all_predicted_correct(self):
        """Test when all predictions are correct but incomplete."""
        pred = [{"row": 0, "col": 0}]
        gt = [{"row": 0, "col": 0}, {"row": 0, "col": 1}]
        score = calculate_header_f1(pred, gt)
        # Precision = 1.0, Recall = 0.5, F1 = 2/3
        assert abs(score - 2 / 3) < 0.01

    def test_all_predicted_wrong(self):
        """Test when all predictions are wrong plus some correct."""
        pred = [{"row": 0, "col": 0}, {"row": 1, "col": 1}]
        gt = [{"row": 0, "col": 0}]
        score = calculate_header_f1(pred, gt)
        # Precision = 0.5, Recall = 1.0, F1 = 2/3
        assert abs(score - 2 / 3) < 0.01

    def test_no_true_positives(self):
        """Test with no true positives."""
        pred = [{"row": 0, "col": 0}]
        gt = [{"row": 1, "col": 1}]
        score = calculate_header_f1(pred, gt)
        assert score == 0.0

    def test_multiple_dimensions(self):
        """Test headers across multiple rows and columns."""
        pred = [
            {"row": 0, "col": i} for i in range(5)
        ]  # First row headers
        gt = [
            {"row": 0, "col": i} for i in range(3)
        ]  # Only first 3 are headers
        score = calculate_header_f1(pred, gt)
        # 3 TP, 2 FP, 0 FN
        # Precision = 3/5 = 0.6, Recall = 3/3 = 1.0
        # F1 = 2 * 0.6 * 1.0 / (0.6 + 1.0) = 0.75
        assert abs(score - 0.75) < 0.01
