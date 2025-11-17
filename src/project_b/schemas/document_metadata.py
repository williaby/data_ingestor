"""
DocumentMetadata Pydantic models for Project B.

This module defines Pydantic v2 models that match the canonical
document_metadata.schema.json from the RAG Pipeline reference docs.

**Input Contract**: Project A (Preprocessing & IQA) → Project B (Layout & OCR)

Schema Version: 1.0.0
Source: docs/Ref Docs/RAG Pipeline/document_metadata.schema.json
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class DocumentTypeEnum(str, Enum):
    """High-level document type classification."""

    IMAGE = "image"
    PDF = "pdf"
    OFFICE_WORD = "office_word"
    OFFICE_EXCEL = "office_excel"
    OFFICE_POWERPOINT = "office_powerpoint"


class PDFTypeEnum(str, Enum):
    """PDF subtype classification per FR-2.1."""

    IMAGE_ONLY = "image_only"
    BORN_DIGITAL = "born_digital"
    HYBRID = "hybrid"


class OCRRoutingRecommendationEnum(str, Enum):
    """Recommended downstream pipeline profile based on DQS and pre_ocr_risk."""

    OCR_FAST = "ocr_fast"
    OCR_ADVANCED = "ocr_advanced"
    VISION_SIMPLE = "vision_simple"
    VISION_STRUCTURED = "vision_structured"


class LayoutTypeEnum(str, Enum):
    """Coarse layout classification informed by OmniDocBench-style attributes."""

    SINGLE_COLUMN = "single_column"
    MULTI_COLUMN = "multi_column"
    THREE_COLUMN = "three_column"
    COMPLEX = "complex"
    UNKNOWN = "unknown"


class DQS(BaseModel):
    """Document Quality Score per FR-7 (degradation and structural complexity)."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=False,
    )

    degradation_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Degradation score (0.0 = pristine, 1.0 = severely degraded)",
    )
    structural_complexity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Structural complexity score (0.0 = simple, 1.0 = very complex)",
    )


class PageAttributes(BaseModel):
    """Page-level visual attributes detected by Project A."""

    model_config = ConfigDict(extra="forbid")

    fuzzy_scan: bool = Field(..., description="True if page appears to be a fuzzy scan")
    watermark: bool = Field(..., description="True if watermark detected")
    colorful_background: bool = Field(
        ..., description="True if colorful background detected"
    )


class PageLayoutSummary(BaseModel):
    """Per-page coarse layout & attribute summary produced by Project A."""

    model_config = ConfigDict(extra="forbid")

    page_index: int = Field(..., ge=0, description="Zero-based page index")
    layout_type: LayoutTypeEnum = Field(
        ..., description="Coarse layout classification"
    )
    has_tables: bool = Field(..., description="True if tables detected on page")
    has_figures: bool = Field(..., description="True if figures/images detected")
    has_dense_math: bool = Field(..., description="True if dense mathematical formulas")
    has_handwriting: bool = Field(..., description="True if handwriting detected")
    page_attributes: PageAttributes = Field(..., description="Visual attributes")


class LearnedQuality(BaseModel):
    """Learned IQA quality metrics from ML model."""

    model_config = ConfigDict(extra="forbid")

    overall_quality: float = Field(
        ..., ge=0.0, le=1.0, description="Overall quality score from ML model"
    )
    sharpness_score: float = Field(
        ..., ge=0.0, le=1.0, description="Learned sharpness score"
    )
    color_fidelity_score: float = Field(
        ..., ge=0.0, le=1.0, description="Learned color fidelity score"
    )


class IQAMetrics(BaseModel):
    """Classical IQA metrics (blur, contrast, noise, etc.)."""

    model_config = ConfigDict(extra="forbid")

    blur_score: Optional[float] = Field(None, description="Blur metric (Laplacian variance)")
    contrast_score: Optional[float] = Field(None, description="Contrast metric")
    noise_score: Optional[float] = Field(None, description="Noise level")
    illumination_score: Optional[float] = Field(None, description="Illumination uniformity")
    skew_angle_deg: Optional[float] = Field(None, description="Skew angle in degrees")
    perspective_score: Optional[float] = Field(None, description="Perspective distortion")
    warping_score: Optional[float] = Field(None, description="Document warping/curling")
    binarization_score: Optional[float] = Field(None, description="Binarization quality")
    bleed_through_score: Optional[float] = Field(None, description="Ink bleed-through severity")


class TransformHistory(BaseModel):
    """Record of corrections attempted/applied by Project A."""

    model_config = ConfigDict(extra="forbid")

    action: str = Field(
        ..., description="Name of the correction (e.g., 'deskew', 'clahe', 'denoise')"
    )
    timestamp: datetime = Field(..., description="When the transform was applied")
    parameters: dict[str, Any] = Field(
        ..., description="Actual parameter values used by the transform"
    )
    skipped: bool = Field(..., description="True if transform was skipped")
    skip_reason: Optional[str] = Field(
        None, description="Reason for skipping (if skipped=True)"
    )


class PageMetadata(BaseModel):
    """Per-page IQA metrics and correction history."""

    model_config = ConfigDict(extra="forbid")

    page_index: int = Field(..., ge=0, description="Zero-based page index")
    width_px: int = Field(..., ge=1, description="Page width in pixels")
    height_px: int = Field(..., ge=1, description="Page height in pixels")
    dpi: Optional[int] = Field(
        None, ge=1, description="Effective DPI after processing; null if unknown"
    )
    has_text: bool = Field(..., description="Result of the text detection gate")
    text_detection_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence of text detection"
    )
    learned_quality: Optional[LearnedQuality] = Field(
        None, description="Learned quality metrics from ML model"
    )
    iqa_metrics: IQAMetrics = Field(..., description="Classical IQA metrics")
    transform_history: list[TransformHistory] = Field(
        ..., description="Record of corrections attempted/applied"
    )


class DocumentMetadata(BaseModel):
    """
    Preprocessing & IQA metadata emitted by Project A.

    This is the **input contract** for Project B (Layout, OCR & Structural Extraction).
    Project A provides preprocessed images and this metadata to inform OCR routing
    and quality-aware processing.

    **Schema Version**: 1.0.0
    **Source**: document_metadata.schema.json
    **Producer**: Project A (Preprocessing & IQA)
    **Consumer**: Project B (Layout & OCR)
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "$schema": "https://json-schema.org/draft/2020-12/schema#",
            "$id": "https://example.com/schemas/document_metadata.schema.json",
        },
    )

    schema_version: str = Field(
        ..., description="Semantic version of this schema, e.g., '1.0.0'"
    )
    document_id: str = Field(
        ..., description="Stable identifier for the logical document (UUID or similar)"
    )
    source_path: Optional[str] = Field(
        None, description="Original file path or URI used at ingestion time"
    )
    source_mime_type: str = Field(
        ..., description="Detected MIME type of the original file, e.g. 'application/pdf'"
    )
    ingested_at: datetime = Field(
        ..., description="Timestamp when Project A ingested this document"
    )
    document_type: DocumentTypeEnum = Field(
        ..., description="High-level document type classification"
    )
    pdf_type: Optional[PDFTypeEnum] = Field(
        None, description="PDF subtype classification per FR-2.1; null for non-PDFs"
    )
    languages: list[str] = Field(
        default_factory=list,
        description="Detected language codes (BCP-47 / ISO 639-1)",
    )
    has_non_latin: Optional[bool] = Field(
        None, description="True if non-Latin scripts are present"
    )
    page_count: int = Field(
        ..., ge=1, description="Total number of pages detected in the document"
    )
    pre_ocr_risk: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Aggregated risk score that OCR will struggle",
    )
    dqs: DQS = Field(
        ..., description="Document Quality Score (degradation and structural complexity)"
    )
    ocr_routing_recommendation: OCRRoutingRecommendationEnum = Field(
        ..., description="Recommended downstream pipeline profile based on DQS"
    )
    page_layout_summary: list[PageLayoutSummary] = Field(
        ..., description="Per-page coarse layout & attribute summary"
    )
    pages: list[PageMetadata] = Field(
        ..., description="Per-page IQA metrics and correction history"
    )


# Type alias for convenience
DocumentMetadataInput = DocumentMetadata
