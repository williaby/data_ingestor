"""
OCRDocument Pydantic models for Project B.

This module defines Pydantic v2 models that match the canonical
ocr_document.schema.json from the RAG Pipeline reference docs.

**Output Contract**: Project B (Layout & OCR) → Project C (Fusion & Chunking)

Schema Version: 1.0.0
Source: docs/Ref Docs/RAG Pipeline/ocr_document.schema.json
"""

from enum import Enum
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field


# Type aliases for clarity
Bbox = Annotated[
    list[float],
    Field(
        min_length=4,
        max_length=4,
        description="COCO format bounding box [x, y, width, height] in pixels",
    ),
]


class ClassLabelEnum(str, Enum):
    """DocLayNet-style layout block classification labels."""

    CAPTION = "caption"
    FOOTNOTE = "footnote"
    FORMULA = "formula"
    LIST_ITEM = "list_item"
    PAGE_FOOTER = "page_footer"
    PAGE_HEADER = "page_header"
    PICTURE = "picture"
    SECTION_HEADER = "section_header"
    TABLE = "table"
    TEXT = "text"
    TITLE = "title"
    HANDWRITING = "handwriting"  # Extension beyond DocLayNet 11 classes
    REVISION_MARKING = "revision_marking"  # Extension beyond DocLayNet 11 classes


class StructuralRoleEnum(str, Enum):
    """Structural role classification for paragraphs."""

    BODY_TEXT = "body_text"
    TITLE = "title"
    SECTION_HEADER = "section_header"
    CAPTION = "caption"
    FOOTNOTE = "footnote"
    TABLE_CONTEXT = "table_context"
    FIGURE_CONTEXT = "figure_context"
    EQUATION_CONTEXT = "equation_context"
    OTHER = "other"


class LayoutBlock(BaseModel):
    """DocLayNet-style layout block with class label and bounding box."""

    model_config = ConfigDict(extra="forbid")

    block_id: str = Field(..., description="Unique identifier for this layout block")
    class_label: ClassLabelEnum = Field(
        ..., description="DocLayNet class label for this block"
    )
    bbox: Bbox = Field(..., description="COCO format [x, y, width, height] in pixels")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score from layout detection model"
    )
    reading_order_index: int = Field(
        ..., description="Order of this block in the reading sequence for this page"
    )


class OCREngineOutput(BaseModel):
    """OCR output from a single engine."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(..., description="Extracted text from OCR engine")
    confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Confidence score for OCR result"
    )


class OCREnginesResult(BaseModel):
    """Per-engine OCR outputs for a paragraph."""

    model_config = ConfigDict(extra="forbid")

    marker: OCREngineOutput = Field(..., description="Marker + Llama 4 OCR result (required)")
    deepseek_ocr: Optional[OCREngineOutput] = Field(
        None, description="DeepSeek-OCR result (optional fallback)"
    )


class Paragraph(BaseModel):
    """Paragraph-level text segment with multi-engine OCR results."""

    model_config = ConfigDict(extra="forbid")

    paragraph_id: str = Field(..., description="Unique identifier for this paragraph")
    page_index: int = Field(..., ge=0, description="Zero-based page index")
    layout_block_id: str = Field(
        ..., description="ID of the primary layout block anchoring this paragraph"
    )
    heading_path: list[str] = Field(
        default_factory=list,
        description="Hierarchy of headings/subheadings enclosing this paragraph",
    )
    structural_role: StructuralRoleEnum = Field(
        ..., description="Structural role classification"
    )
    reading_order_index: int = Field(
        ..., description="Global reading order position within the document"
    )
    ocr_engines: OCREnginesResult = Field(
        ..., description="Per-engine OCR outputs for this paragraph"
    )
    languages: list[str] = Field(
        default_factory=list, description="Detected language codes in this paragraph"
    )
    has_math: Optional[bool] = Field(
        None, description="True if paragraph contains mathematical formulas"
    )
    has_table_ref: Optional[bool] = Field(
        None, description="True if paragraph is a table or references tables strongly"
    )
    has_handwriting: Optional[bool] = Field(
        None, description="True if paragraph contains handwriting"
    )


class OCRPage(BaseModel):
    """Per-page layout and OCR details."""

    model_config = ConfigDict(extra="forbid")

    page_index: int = Field(..., ge=0, description="Zero-based page index")
    width_px: int = Field(..., ge=1, description="Page width in pixels")
    height_px: int = Field(..., ge=1, description="Page height in pixels")
    layout_blocks: list[LayoutBlock] = Field(
        ..., description="DocLayNet-style blocks with class labels and bounding boxes"
    )
    reading_order: list[str] = Field(
        ..., description="Ordered list of block_ids representing page reading flow"
    )
    paragraphs: list[Paragraph] = Field(
        ..., description="Paragraph-level text segments produced by OCR engines"
    )


class OCRDocument(BaseModel):
    """
    Structured layout and OCR output emitted by Project B.

    This is the **output contract** for Project B (Layout, OCR & Structural Extraction)
    and the **input contract** for Project C (Fusion & Chunking Engine).

    **Schema Version**: 1.0.0
    **Source**: ocr_document.schema.json
    **Producer**: Project B (Layout & OCR)
    **Consumer**: Project C (Fusion & Chunking)
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "$schema": "https://json-schema.org/draft/2020-12/schema#",
            "$id": "https://example.com/schemas/ocr_document.schema.json",
        },
    )

    schema_version: str = Field(
        ..., description="Semantic version of this schema, e.g., '1.0.0'"
    )
    document_id: str = Field(
        ..., description="Stable identifier matching DocumentMetadata.document_id"
    )
    source_document_metadata_id: Optional[str] = Field(
        None,
        description="Identifier of the corresponding DocumentMetadata record (if persisted separately)",
    )
    page_count: int = Field(..., ge=1, description="Total number of pages in document")
    layout_model_name: str = Field(
        ...,
        description="Identifier of the layout detection model used (e.g., 'yolov10_doc_v1')",
    )
    ocr_engines: list[str] = Field(
        ...,
        description="List of OCR engines participating in this run (e.g., ['marker', 'deepseek_ocr'])",
    )
    pages: list[OCRPage] = Field(..., description="Per-page layout and OCR details")


# Type alias for convenience
OCRDocumentOutput = OCRDocument
