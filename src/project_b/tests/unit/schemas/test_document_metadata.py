"""
Unit tests for DocumentMetadata Pydantic models.

Tests that the Pydantic models correctly match the canonical JSON schema
from document_metadata.schema.json.
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from project_b.schemas.document_metadata import (
    DQS,
    DocumentMetadata,
    DocumentTypeEnum,
    IQAMetrics,
    LayoutTypeEnum,
    LearnedQuality,
    OCRRoutingRecommendationEnum,
    PageAttributes,
    PageLayoutSummary,
    PageMetadata,
    PDFTypeEnum,
    TransformHistory,
)


class TestDQS:
    """Test DQS (Document Quality Score) model."""

    def test_valid_dqs(self):
        """Test valid DQS with scores in range."""
        dqs = DQS(degradation_score=0.3, structural_complexity_score=0.7)
        assert dqs.degradation_score == 0.3
        assert dqs.structural_complexity_score == 0.7

    def test_dqs_score_range_validation(self):
        """Test DQS scores must be between 0.0 and 1.0."""
        # Valid edge cases
        DQS(degradation_score=0.0, structural_complexity_score=1.0)
        DQS(degradation_score=1.0, structural_complexity_score=0.0)

        # Invalid: out of range
        with pytest.raises(ValidationError):
            DQS(degradation_score=-0.1, structural_complexity_score=0.5)

        with pytest.raises(ValidationError):
            DQS(degradation_score=0.5, structural_complexity_score=1.1)

    def test_dqs_no_extra_fields(self):
        """Test DQS rejects extra fields."""
        with pytest.raises(ValidationError):
            DQS(
                degradation_score=0.5,
                structural_complexity_score=0.5,
                extra_field="invalid",
            )


class TestPageAttributes:
    """Test PageAttributes model."""

    def test_valid_page_attributes(self):
        """Test valid page attributes."""
        attrs = PageAttributes(
            fuzzy_scan=True, watermark=False, colorful_background=True
        )
        assert attrs.fuzzy_scan is True
        assert attrs.watermark is False
        assert attrs.colorful_background is True

    def test_page_attributes_required_fields(self):
        """Test all page attribute fields are required."""
        with pytest.raises(ValidationError):
            PageAttributes(fuzzy_scan=True)  # Missing watermark, colorful_background


class TestPageLayoutSummary:
    """Test PageLayoutSummary model."""

    def test_valid_page_layout_summary(self):
        """Test valid page layout summary."""
        summary = PageLayoutSummary(
            page_index=0,
            layout_type=LayoutTypeEnum.SINGLE_COLUMN,
            has_tables=True,
            has_figures=False,
            has_dense_math=False,
            has_handwriting=False,
            page_attributes=PageAttributes(
                fuzzy_scan=False, watermark=False, colorful_background=False
            ),
        )
        assert summary.page_index == 0
        assert summary.layout_type == LayoutTypeEnum.SINGLE_COLUMN
        assert summary.has_tables is True

    def test_layout_type_enum_validation(self):
        """Test layout_type must be valid enum value."""
        with pytest.raises(ValidationError):
            PageLayoutSummary(
                page_index=0,
                layout_type="invalid_layout",  # Invalid enum value
                has_tables=False,
                has_figures=False,
                has_dense_math=False,
                has_handwriting=False,
                page_attributes=PageAttributes(
                    fuzzy_scan=False, watermark=False, colorful_background=False
                ),
            )


class TestIQAMetrics:
    """Test IQAMetrics model."""

    def test_valid_iqa_metrics_all_fields(self):
        """Test IQA metrics with all fields populated."""
        metrics = IQAMetrics(
            blur_score=0.85,
            contrast_score=0.75,
            noise_score=0.12,
            illumination_score=0.88,
            skew_angle_deg=0.5,
            perspective_score=0.95,
            warping_score=0.02,
            binarization_score=0.90,
            bleed_through_score=0.05,
        )
        assert metrics.blur_score == 0.85
        assert metrics.skew_angle_deg == 0.5

    def test_iqa_metrics_optional_fields(self):
        """Test IQA metrics with all fields optional."""
        metrics = IQAMetrics()  # All fields are optional
        assert metrics.blur_score is None
        assert metrics.contrast_score is None


class TestTransformHistory:
    """Test TransformHistory model."""

    def test_valid_transform_history(self):
        """Test valid transform history entry."""
        now = datetime.now(timezone.utc)
        transform = TransformHistory(
            action="deskew",
            timestamp=now,
            parameters={"angle": -2.5, "method": "shear"},
            skipped=False,
            skip_reason=None,
        )
        assert transform.action == "deskew"
        assert transform.skipped is False
        assert transform.parameters["angle"] == -2.5

    def test_transform_history_skipped(self):
        """Test transform history with skipped=True."""
        now = datetime.now(timezone.utc)
        transform = TransformHistory(
            action="denoise",
            timestamp=now,
            parameters={},
            skipped=True,
            skip_reason="Image quality already high",
        )
        assert transform.skipped is True
        assert transform.skip_reason == "Image quality already high"


class TestPageMetadata:
    """Test PageMetadata model."""

    def test_valid_page_metadata(self):
        """Test valid page metadata."""
        page = PageMetadata(
            page_index=0,
            width_px=595,
            height_px=842,
            dpi=300,
            has_text=True,
            text_detection_confidence=0.95,
            learned_quality=LearnedQuality(
                overall_quality=0.88,
                sharpness_score=0.85,
                color_fidelity_score=0.90,
            ),
            iqa_metrics=IQAMetrics(blur_score=0.85, contrast_score=0.75),
            transform_history=[
                TransformHistory(
                    action="deskew",
                    timestamp=datetime.now(timezone.utc),
                    parameters={"angle": -1.2},
                    skipped=False,
                )
            ],
        )
        assert page.width_px == 595
        assert page.height_px == 842
        assert page.has_text is True

    def test_page_metadata_dimension_validation(self):
        """Test page dimensions must be >= 1."""
        with pytest.raises(ValidationError):
            PageMetadata(
                page_index=0,
                width_px=0,  # Invalid: must be >= 1
                height_px=842,
                has_text=True,
                text_detection_confidence=0.95,
                iqa_metrics=IQAMetrics(),
                transform_history=[],
            )


class TestDocumentMetadata:
    """Test DocumentMetadata main model."""

    def test_valid_document_metadata_minimal(self):
        """Test minimal valid DocumentMetadata."""
        now = datetime.now(timezone.utc)
        doc = DocumentMetadata(
            schema_version="1.0.0",
            document_id="test-doc-001",
            source_mime_type="application/pdf",
            ingested_at=now,
            document_type=DocumentTypeEnum.PDF,
            pdf_type=PDFTypeEnum.BORN_DIGITAL,
            page_count=1,
            pre_ocr_risk=0.15,
            dqs=DQS(degradation_score=0.05, structural_complexity_score=0.6),
            ocr_routing_recommendation=OCRRoutingRecommendationEnum.OCR_FAST,
            page_layout_summary=[
                PageLayoutSummary(
                    page_index=0,
                    layout_type=LayoutTypeEnum.SINGLE_COLUMN,
                    has_tables=False,
                    has_figures=False,
                    has_dense_math=False,
                    has_handwriting=False,
                    page_attributes=PageAttributes(
                        fuzzy_scan=False, watermark=False, colorful_background=False
                    ),
                )
            ],
            pages=[
                PageMetadata(
                    page_index=0,
                    width_px=595,
                    height_px=842,
                    dpi=300,
                    has_text=True,
                    text_detection_confidence=0.98,
                    iqa_metrics=IQAMetrics(blur_score=0.9),
                    transform_history=[],
                )
            ],
        )
        assert doc.document_id == "test-doc-001"
        assert doc.page_count == 1
        assert doc.pdf_type == PDFTypeEnum.BORN_DIGITAL

    def test_document_metadata_enum_validation(self):
        """Test document_type and pdf_type enum validation."""
        now = datetime.now(timezone.utc)

        # Invalid document_type
        with pytest.raises(ValidationError):
            DocumentMetadata(
                schema_version="1.0.0",
                document_id="test",
                source_mime_type="application/pdf",
                ingested_at=now,
                document_type="invalid_type",  # Invalid enum
                page_count=1,
                pre_ocr_risk=0.1,
                dqs=DQS(degradation_score=0.1, structural_complexity_score=0.1),
                ocr_routing_recommendation=OCRRoutingRecommendationEnum.OCR_FAST,
                page_layout_summary=[],
                pages=[],
            )

    def test_document_metadata_pdf_type_null_for_non_pdf(self):
        """Test pdf_type can be null for non-PDF documents."""
        now = datetime.now(timezone.utc)
        doc = DocumentMetadata(
            schema_version="1.0.0",
            document_id="test-image-001",
            source_mime_type="image/jpeg",
            ingested_at=now,
            document_type=DocumentTypeEnum.IMAGE,
            pdf_type=None,  # Should be null for non-PDF
            page_count=1,
            pre_ocr_risk=0.1,
            dqs=DQS(degradation_score=0.1, structural_complexity_score=0.1),
            ocr_routing_recommendation=OCRRoutingRecommendationEnum.VISION_SIMPLE,
            page_layout_summary=[],
            pages=[],
        )
        assert doc.pdf_type is None
        assert doc.document_type == DocumentTypeEnum.IMAGE

    def test_document_metadata_no_extra_fields(self):
        """Test DocumentMetadata rejects extra fields."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            DocumentMetadata(
                schema_version="1.0.0",
                document_id="test",
                source_mime_type="application/pdf",
                ingested_at=now,
                document_type=DocumentTypeEnum.PDF,
                page_count=1,
                pre_ocr_risk=0.1,
                dqs=DQS(degradation_score=0.1, structural_complexity_score=0.1),
                ocr_routing_recommendation=OCRRoutingRecommendationEnum.OCR_FAST,
                page_layout_summary=[],
                pages=[],
                extra_field="invalid",  # Extra field should be rejected
            )

    def test_document_metadata_json_serialization(self):
        """Test DocumentMetadata can serialize to/from JSON."""
        now = datetime.now(timezone.utc)
        doc = DocumentMetadata(
            schema_version="1.0.0",
            document_id="test-doc-001",
            source_mime_type="application/pdf",
            ingested_at=now,
            document_type=DocumentTypeEnum.PDF,
            pdf_type=PDFTypeEnum.HYBRID,
            languages=["en", "es"],
            has_non_latin=False,
            page_count=1,
            pre_ocr_risk=0.25,
            dqs=DQS(degradation_score=0.15, structural_complexity_score=0.5),
            ocr_routing_recommendation=OCRRoutingRecommendationEnum.OCR_ADVANCED,
            page_layout_summary=[],
            pages=[],
        )

        # Serialize to JSON
        json_str = doc.model_dump_json()
        assert "test-doc-001" in json_str

        # Deserialize from JSON
        doc2 = DocumentMetadata.model_validate_json(json_str)
        assert doc2.document_id == doc.document_id
        assert doc2.pdf_type == doc.pdf_type
        assert doc2.languages == doc.languages
