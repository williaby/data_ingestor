"""
PubTables-1M dataset evaluator.

Evaluates table structure recognition quality.

Metrics:
- TEDS: Tree Edit Distance Score (overall table structure)
- Cell Exact Match: Cell-level content accuracy
- Header F1: Header row/column detection
"""

from pathlib import Path
from typing import Dict, List

from data_ingestor.core.models import Document
from data_ingestor.evaluation.base import BaseEvaluator
from data_ingestor.evaluation.models import EvaluationResult, MetricScore, MetricType
from data_ingestor.evaluation.metrics import (
    calculate_cell_exact_match,
    calculate_header_f1,
    calculate_teds,
)


class PubTablesEvaluator(BaseEvaluator):
    """
    Evaluator for PubTables-1M dataset (table structure recognition).

    PubTables-1M provides detailed table structure annotations including:
    - Row/column spans
    - Merged cells
    - Header vs. data cell classification
    - Cell content
    """

    def __init__(self, ground_truth_dir: Path):
        """
        Initialize PubTables evaluator.

        Args:
            ground_truth_dir: Path to PubTables ground truth annotations (JSON)
        """
        super().__init__("pubtables", ground_truth_dir)

    def evaluate_document(
        self,
        predicted: Document,
        ground_truth: Dict,
    ) -> EvaluationResult:
        """
        Evaluate a table against PubTables ground truth.

        Args:
            predicted: Parsed document (should contain single table)
            ground_truth: Dict with table structure annotations

        Returns:
            EvaluationResult with table structure metrics
        """
        # Validate inputs
        self.validate_document(predicted, ground_truth)

        doc_id = predicted.metadata.get("doc_id", "unknown")
        result = EvaluationResult(
            document_id=doc_id,
            dataset=self.dataset_name,
        )

        try:
            # Extract table structure
            gt_table = ground_truth.get("table_structure", {})
            if not gt_table:
                raise ValueError("Ground truth table structure missing")

            # Find table element in predicted document
            # #ASSUME: Document contains exactly one table element
            # #VERIFY: Table element exists and has proper structure
            pred_table = self._extract_table(predicted)
            if not pred_table:
                raise ValueError("No table found in predicted document")

            # Calculate TEDS (Tree Edit Distance Score)
            teds = calculate_teds(pred_table, gt_table)

            result.metrics.append(
                MetricScore(
                    name=MetricType.TEDS,
                    value=teds,
                    metadata={
                        "pred_rows": len(pred_table.get("rows", [])),
                        "pred_cols": len(pred_table.get("cols", [])),
                        "gt_rows": len(gt_table.get("rows", [])),
                        "gt_cols": len(gt_table.get("cols", [])),
                    },
                )
            )

            # Calculate cell-level metrics
            pred_cells = pred_table.get("cells", [])
            gt_cells = gt_table.get("cells", [])

            cell_match = calculate_cell_exact_match(pred_cells, gt_cells)

            result.metrics.append(
                MetricScore(
                    name=MetricType.CELL_MATCH,
                    value=cell_match,
                    metadata={
                        "pred_cells": len(pred_cells),
                        "gt_cells": len(gt_cells),
                    },
                )
            )

            # Calculate header detection metrics
            pred_headers = [c for c in pred_cells if c.get("is_header", False)]
            gt_headers = [c for c in gt_cells if c.get("is_header", False)]

            header_f1 = calculate_header_f1(pred_headers, gt_headers)

            result.metrics.append(
                MetricScore(
                    name=MetricType.HEADER_F1,
                    value=header_f1,
                    metadata={
                        "pred_headers": len(pred_headers),
                        "gt_headers": len(gt_headers),
                    },
                )
            )

        except Exception as e:
            result.success = False
            result.error = str(e)

        return result

    def _extract_table(self, document: Document) -> Dict:
        """
        Extract table structure from document.

        Args:
            document: Parsed document

        Returns:
            Table structure dict
        """
        # Find first table element
        for element in document.elements:
            if element.type == "Table":
                return self._element_to_table_structure(element)

        return {}

    def _element_to_table_structure(self, element) -> Dict:
        """
        Convert table element to structure dict.

        Args:
            element: Table element

        Returns:
            Table structure dict with rows, cols, cells
        """
        # #ASSUME: Table element has structured metadata
        # #VERIFY: Metadata contains rows, columns, cells information

        table = {
            "rows": [],
            "cols": [],
            "cells": [],
        }

        # Extract from metadata if available
        if "table_structure" in element.metadata:
            table.update(element.metadata["table_structure"])
        elif "rows" in element.metadata:
            # Alternative format
            table["rows"] = element.metadata.get("rows", [])
            table["cols"] = element.metadata.get("cols", [])
            table["cells"] = element.metadata.get("cells", [])

        # Fallback: parse from text (simplified)
        if not table["cells"] and element.text:
            table["cells"] = self._parse_table_text(element.text)

        return table

    def _parse_table_text(self, table_text: str) -> List[Dict]:
        """
        Parse table text into cell structure (simplified).

        Args:
            table_text: Table as text (markdown or plain text)

        Returns:
            List of cell dicts with row, col, text
        """
        cells = []

        # Simple parsing for markdown tables
        # TODO(Phase 1.5): Implement robust table parsing
        lines = table_text.strip().split("\n")
        for row_idx, line in enumerate(lines):
            if "|" in line:
                # Markdown table row
                cols = [c.strip() for c in line.split("|") if c.strip()]
                for col_idx, text in enumerate(cols):
                    cells.append(
                        {
                            "row": row_idx,
                            "col": col_idx,
                            "text": text,
                            "is_header": row_idx == 0,  # First row as header
                        }
                    )

        return cells

    def get_baseline_targets(self) -> Dict[str, float]:
        """Get PubTables baseline targets from Phase 1.5 config."""
        return {
            MetricType.TEDS: 0.75,
            MetricType.CELL_MATCH: 0.70,
            MetricType.HEADER_F1: 0.80,
        }
