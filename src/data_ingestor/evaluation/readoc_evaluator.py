"""
ReadOC dataset evaluator.

Evaluates PDF→Markdown structure fidelity, which is the best proxy for
RAG chunk quality.

Metrics:
- Section F1: Heading detection and hierarchy
- List F1: List extraction accuracy
- Table F1: Table-to-markdown conversion
- Text CER: Character Error Rate
- BLEU/chrF: Text similarity
"""

from pathlib import Path
from typing import Dict

from data_ingestor.core.models import Document
from data_ingestor.evaluation.base import BaseEvaluator
from data_ingestor.evaluation.models import EvaluationResult, MetricScore, MetricType
from data_ingestor.evaluation.metrics import (
    calculate_bleu,
    calculate_cer,
    calculate_chrf,
    calculate_section_f1,
)


class ReadOCEvaluator(BaseEvaluator):
    """
    Evaluator for ReadOC dataset (PDF→Markdown).

    ReadOC pairs PDFs with ground truth Markdown, making it ideal for
    evaluating end-to-end structure fidelity for RAG applications.
    """

    def __init__(self, ground_truth_dir: Path):
        """
        Initialize ReadOC evaluator.

        Args:
            ground_truth_dir: Path to ReadOC ground truth markdown files
        """
        super().__init__("readoc", ground_truth_dir)

    def evaluate_document(
        self,
        predicted: Document,
        ground_truth: Dict,
    ) -> EvaluationResult:
        """
        Evaluate a document against ReadOC ground truth.

        Args:
            predicted: Parsed document from our pipeline
            ground_truth: Dict with 'markdown' key containing ground truth text

        Returns:
            EvaluationResult with metrics
        """
        # Validate inputs
        self.validate_document(predicted, ground_truth)

        doc_id = predicted.metadata.get("doc_id", "unknown")
        result = EvaluationResult(
            document_id=doc_id,
            dataset=self.dataset_name,
        )

        try:
            # Extract ground truth markdown
            gt_markdown = ground_truth.get("markdown", "")
            if not gt_markdown:
                raise ValueError("Ground truth markdown is empty")

            # Convert predicted document to markdown
            # #ASSUME: Document has elements that can be converted to markdown
            # #VERIFY: Markdown conversion produces valid output
            pred_markdown = self._document_to_markdown(predicted)

            # Calculate text fidelity metrics
            cer = calculate_cer(pred_markdown, gt_markdown)
            bleu = calculate_bleu(pred_markdown, gt_markdown)
            chrf = calculate_chrf(pred_markdown, gt_markdown)

            result.metrics.extend(
                [
                    MetricScore(
                        name=MetricType.CER,
                        value=cer,
                        metadata={"lower_is_better": True},
                    ),
                    MetricScore(name=MetricType.BLEU, value=bleu),
                    MetricScore(name=MetricType.CHRF, value=chrf),
                ]
            )

            # Extract sections for structure metrics
            pred_sections = self._extract_sections(predicted)
            gt_sections = self._extract_sections_from_markdown(gt_markdown)

            # Calculate structure metrics
            section_f1 = calculate_section_f1(pred_sections, gt_sections)

            result.metrics.append(
                MetricScore(
                    name=MetricType.SECTION_F1,
                    value=section_f1,
                    metadata={
                        "pred_sections": len(pred_sections),
                        "gt_sections": len(gt_sections),
                    },
                )
            )

            # TODO(Phase 1.5): Add list F1 metric
            # TODO(Phase 1.5): Add table F1 metric for table-to-markdown conversion

        except Exception as e:
            result.success = False
            result.error = str(e)

        return result

    def _document_to_markdown(self, document: Document) -> str:
        """
        Convert Document to markdown text.

        Args:
            document: Parsed document

        Returns:
            Markdown text
        """
        lines = []

        for element in document.elements:
            # Handle different element types
            if element.type == "Title":
                lines.append(f"# {element.text}\n")
            elif element.type == "Section-header":
                # Estimate level from metadata or default to ##
                level = element.metadata.get("level", 2)
                prefix = "#" * level
                lines.append(f"{prefix} {element.text}\n")
            elif element.type == "List-item":
                lines.append(f"- {element.text}\n")
            elif element.type == "Table":
                # Simple table representation
                lines.append(f"\n{element.text}\n")
            else:
                # Regular text
                lines.append(f"{element.text}\n")

        return "\n".join(lines)

    def _extract_sections(self, document: Document) -> list:
        """
        Extract sections (headings) from document.

        Args:
            document: Parsed document

        Returns:
            List of (heading_text, level) tuples
        """
        sections = []

        for element in document.elements:
            if element.type in ["Title", "Section-header"]:
                level = 1 if element.type == "Title" else element.metadata.get("level", 2)
                sections.append((element.text, level))

        return sections

    def _extract_sections_from_markdown(self, markdown: str) -> list:
        """
        Extract sections from markdown text.

        Args:
            markdown: Markdown text

        Returns:
            List of (heading_text, level) tuples
        """
        sections = []

        for line in markdown.split("\n"):
            line = line.strip()
            if line.startswith("#"):
                # Count heading level
                level = len(line) - len(line.lstrip("#"))
                text = line.lstrip("#").strip()
                sections.append((text, level))

        return sections

    def get_baseline_targets(self) -> Dict[str, float]:
        """Get ReadOC baseline targets from Phase 1.5 config."""
        return {
            MetricType.SECTION_F1: 0.75,
            MetricType.LIST_F1: 0.70,
            "table_f1": 0.75,
            MetricType.CER: 0.10,  # Lower is better
        }
