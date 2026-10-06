"""Generated Docling documents and fakes for conversion and chunking tests.

Everything here is synthetic; no real document content is used.
"""

from typing import Any

from docling_core.transforms.chunker.tokenizer.base import BaseTokenizer
from docling_core.types.doc import (
    BoundingBox,
    CoordOrigin,
    DocItemLabel,
    DoclingDocument,
    ProvenanceItem,
    Size,
    TableCell,
    TableData,
)


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


def _table_data(rows: int, cols: int) -> TableData:
    cells = [
        TableCell(
            text=f"h{col}" if row == 0 else f"r{row}c{col}",
            start_row_offset_idx=row,
            end_row_offset_idx=row + 1,
            start_col_offset_idx=col,
            end_col_offset_idx=col + 1,
            column_header=row == 0,
        )
        for row in range(rows)
        for col in range(cols)
    ]
    return TableData(num_rows=rows, num_cols=cols, table_cells=cells)


def build_large_table_docling_json(rows: int = 40, cols: int = 3, heading_words: int = 7) -> dict[str, Any]:
    """One page: a heading of ``heading_words`` words above a table too big for one chunk."""
    doc = DoclingDocument(name="large-table")
    doc.add_page(page_no=1, size=Size(width=612, height=792))
    heading = doc.add_heading(sentence_block("head", heading_words), level=1, prov=_prov(1))
    doc.add_table(data=_table_data(rows, cols), parent=heading, prov=_prov(1))
    return doc.export_to_dict()


def build_long_heading_docling_json(heading_words: int = 40) -> dict[str, Any]:
    """One page: a heading longer than a small token cap above a short paragraph."""
    doc = DoclingDocument(name="long-heading")
    doc.add_page(page_no=1, size=Size(width=612, height=792))
    heading = doc.add_heading(sentence_block("head", heading_words), level=1, prov=_prov(1))
    doc.add_text(label="text", text=sentence_block("body", 10), parent=heading, prov=_prov(1))
    return doc.export_to_dict()


def build_multi_page_section_docling_json() -> dict[str, Any]:
    """One heading with a short paragraph on page 1 and another on page 2 (merged into one chunk)."""
    doc = DoclingDocument(name="multi-page")
    for page in (1, 2):
        doc.add_page(page_no=page, size=Size(width=612, height=792))
    heading = doc.add_heading("Spanning section", level=1, prov=_prov(1))
    doc.add_text(label="text", text=sentence_block("first", 5), parent=heading, prov=_prov(1))
    doc.add_text(label="text", text=sentence_block("second", 5), parent=heading, prov=_prov(2))
    return doc.export_to_dict()


def build_branch_docling_json() -> dict[str, Any]:
    """A document with a list, code, a formula, a picture, an empty text and a bottom-left bbox."""
    doc = DoclingDocument(name="branches")
    doc.add_page(page_no=1, size=Size(width=612, height=792))
    doc.add_title("Branch Title", prov=_prov(1))
    section = doc.add_heading("Section", level=3, prov=_prov(1))
    group = doc.add_list_group(parent=section)
    doc.add_list_item("first bullet", parent=group, prov=_prov(1))
    doc.add_code("print('hi')", parent=section, prov=_prov(1))
    doc.add_text(label=DocItemLabel.FORMULA, text="E = mc^2", parent=section, prov=_prov(1))
    doc.add_text(label="text", text="   ", parent=section, prov=_prov(1))
    doc.add_picture(parent=section, prov=_prov(1))
    bottom_left = ProvenanceItem(
        page_no=1,
        bbox=BoundingBox(l=10, t=700, r=200, b=680, coord_origin=CoordOrigin.BOTTOMLEFT),
        charspan=(0, 1),
    )
    doc.add_text(label="text", text="bottom left paragraph", parent=section, prov=bottom_left)
    return doc.export_to_dict()
