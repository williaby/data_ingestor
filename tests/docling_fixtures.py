"""Generated Docling documents and fakes for conversion and chunking tests.

Everything here is synthetic; no real document content is used.
"""

from typing import Any

from docling_core.transforms.chunker.tokenizer.base import BaseTokenizer
from docling_core.types.doc import BoundingBox, DoclingDocument, ProvenanceItem, Size, TableCell, TableData


class WordTokenizer(BaseTokenizer):
    """Whitespace tokenizer with a configurable cap, for offline unit tests."""

    max_tokens: int = 64

    def count_tokens(self, text: str) -> int:
        return len(text.split())

    def get_max_tokens(self) -> int:
        return self.max_tokens

    def get_tokenizer(self) -> Any:
        return self.count_tokens  # semchunk accepts a token-counting callable


def _prov(page: int) -> ProvenanceItem:
    return ProvenanceItem(page_no=page, bbox=BoundingBox(l=10, t=20, r=200, b=40), charspan=(0, 1))


def sentence_block(prefix: str, words: int) -> str:
    return " ".join(f"{prefix}{i}" for i in range(words))


def build_sample_docling_json(with_pages: bool = True) -> dict[str, Any]:
    """A three-page synthetic document with headings, paragraphs, a list and a table."""
    doc = DoclingDocument(name="synthetic-sample")
    for page in (1, 2, 3):
        doc.add_page(page_no=page, size=Size(width=612, height=792))

    def prov(page: int) -> ProvenanceItem | None:
        return _prov(page) if with_pages else None

    doc.add_title("Synthetic Sample Report", prov=prov(1))
    intro = doc.add_heading("Introduction", level=1, prov=prov(1))
    doc.add_text(label="text", text=sentence_block("intro", 30), parent=intro, prov=prov(1))
    doc.add_text(label="text", text=sentence_block("scope", 30), parent=intro, prov=prov(1))

    body = doc.add_heading("Findings", level=1, prov=prov(2))
    doc.add_text(label="text", text=sentence_block("finding", 150), parent=body, prov=prov(2))
    cells = [
        TableCell(
            text="Item",
            start_row_offset_idx=0,
            end_row_offset_idx=1,
            start_col_offset_idx=0,
            end_col_offset_idx=1,
            column_header=True,
        ),
        TableCell(
            text="Count",
            start_row_offset_idx=0,
            end_row_offset_idx=1,
            start_col_offset_idx=1,
            end_col_offset_idx=2,
            column_header=True,
        ),
        TableCell(
            text="Widgets",
            start_row_offset_idx=1,
            end_row_offset_idx=2,
            start_col_offset_idx=0,
            end_col_offset_idx=1,
        ),
        TableCell(
            text="42",
            start_row_offset_idx=1,
            end_row_offset_idx=2,
            start_col_offset_idx=1,
            end_col_offset_idx=2,
        ),
    ]
    doc.add_table(data=TableData(num_rows=2, num_cols=2, table_cells=cells), parent=body, prov=prov(2))

    outro = doc.add_heading("Conclusion", level=1, prov=prov(3))
    doc.add_text(label="text", text=sentence_block("close", 20), parent=outro, prov=prov(3))
    return doc.export_to_dict()
