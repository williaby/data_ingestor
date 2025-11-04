"""
Metric calculation functions for evaluation.

Provides implementations of standard metrics used in document parsing evaluation:
- Text fidelity: CER, BLEU, chrF
- Structure: Section F1, Reading order, Kendall tau
- Tables: TEDS, Cell match, Header F1
- Layout: mAP for layout detection
"""

from data_ingestor.evaluation.metrics.text_metrics import (
    calculate_bleu,
    calculate_cer,
    calculate_chrf,
)
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
from data_ingestor.evaluation.metrics.layout_metrics import calculate_map

__all__ = [
    # Text metrics
    "calculate_cer",
    "calculate_bleu",
    "calculate_chrf",
    # Structure metrics
    "calculate_section_f1",
    "calculate_reading_order_f1",
    "calculate_kendall_tau",
    # Table metrics
    "calculate_teds",
    "calculate_cell_exact_match",
    "calculate_header_f1",
    # Layout metrics
    "calculate_map",
]
