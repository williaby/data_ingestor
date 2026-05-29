"""
Metric calculation functions for evaluation.

Provides implementations of standard metrics used in document parsing evaluation:
- Text fidelity: CER, BLEU, chrF
- Structure: Section F1, Reading order, Kendall tau
- Tables: TEDS, Cell match, Header F1
- Layout: mAP for layout detection
"""

from data_ingestor.evaluation.metrics.layout_metrics import calculate_map
from data_ingestor.evaluation.metrics.structure_metrics import (
    calculate_kendall_tau,
    calculate_reading_order_f1,
    calculate_section_f1,
)
from data_ingestor.evaluation.metrics.table_metrics import (
    calculate_cell_exact_match,
    calculate_header_f1,
    calculate_teds,
)
from data_ingestor.evaluation.metrics.text_metrics import (
    calculate_bleu,
    calculate_cer,
    calculate_chrf,
)

__all__ = [
    "calculate_bleu",
    "calculate_cell_exact_match",
    # Text metrics
    "calculate_cer",
    "calculate_chrf",
    "calculate_header_f1",
    "calculate_kendall_tau",
    # Layout metrics
    "calculate_map",
    "calculate_reading_order_f1",
    # Structure metrics
    "calculate_section_f1",
    # Table metrics
    "calculate_teds",
]
