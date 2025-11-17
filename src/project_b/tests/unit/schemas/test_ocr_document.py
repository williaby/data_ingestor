"""
Unit tests for OCRDocument Pydantic models.

Tests that the Pydantic models correctly match the canonical JSON schema
from ocr_document.schema.json.
"""

import pytest
from pydantic import ValidationError

from project_b.schemas.ocr_document import (
    ClassLabelEnum,
    LayoutBlock,
    OCRDocument,
    OCREngineOutput,
    OCREnginesResult,
    OCRPage,
    Paragraph,
    StructuralRoleEnum,
)


class TestLayoutBlock:
    """Test LayoutBlock model."""

    def test_valid_layout_block(self):
        """Test valid layout block with all fields."""
        block = LayoutBlock(
            block_id="b001",
            class_label=ClassLabelEnum.TEXT,
            bbox=[50.0, 100.0, 495.0, 50.0],
            confidence=0.95,
            reading_order_index=1,
        )
        assert block.block_id == "b001"
        assert block.class_label == ClassLabelEnum.TEXT
        assert block.bbox == [50.0, 100.0, 495.0, 50.0]
        assert block.confidence == 0.95
        assert block.reading_order_index == 1

    def test_bbox_length_validation(self):
        """Test bbox must have exactly 4 elements."""
        # Valid: exactly 4 elements
        LayoutBlock(
            block_id="b001",
            class_label=ClassLabelEnum.TEXT,
            bbox=[10.0, 20.0, 100.0, 50.0],
            confidence=0.9,
            reading_order_index=1,
        )

        # Invalid: too few elements
        with pytest.raises(ValidationError):
            LayoutBlock(
                block_id="b001",
                class_label=ClassLabelEnum.TEXT,
                bbox=[10.0, 20.0, 100.0],  # Only 3 elements
                confidence=0.9,
                reading_order_index=1,
            )

        # Invalid: too many elements
        with pytest.raises(ValidationError):
            LayoutBlock(
                block_id="b001",
                class_label=ClassLabelEnum.TEXT,
                bbox=[10.0, 20.0, 100.0, 50.0, 30.0],  # 5 elements
                confidence=0.9,
                reading_order_index=1,
            )

    def test_class_label_enum_validation(self):
        """Test class_label must be valid DocLayNet enum."""
        # Valid DocLayNet labels
        for label in [
            ClassLabelEnum.TEXT,
            ClassLabelEnum.TITLE,
            ClassLabelEnum.SECTION_HEADER,
            ClassLabelEnum.TABLE,
            ClassLabelEnum.FORMULA,
            ClassLabelEnum.LIST_ITEM,
            ClassLabelEnum.CAPTION,
            ClassLabelEnum.FOOTNOTE,
            ClassLabelEnum.PAGE_HEADER,
            ClassLabelEnum.PAGE_FOOTER,
            ClassLabelEnum.PICTURE,
            ClassLabelEnum.HANDWRITING,
            ClassLabelEnum.REVISION_MARKING,
        ]:
            LayoutBlock(
                block_id="b001",
                class_label=label,
                bbox=[10.0, 20.0, 100.0, 50.0],
                confidence=0.9,
                reading_order_index=1,
            )

        # Invalid class label
        with pytest.raises(ValidationError):
            LayoutBlock(
                block_id="b001",
                class_label="invalid_label",  # Not in enum
                bbox=[10.0, 20.0, 100.0, 50.0],
                confidence=0.9,
                reading_order_index=1,
            )

    def test_confidence_range_validation(self):
        """Test confidence must be between 0.0 and 1.0."""
        # Valid edge cases
        LayoutBlock(
            block_id="b001",
            class_label=ClassLabelEnum.TEXT,
            bbox=[10.0, 20.0, 100.0, 50.0],
            confidence=0.0,
            reading_order_index=1,
        )
        LayoutBlock(
            block_id="b001",
            class_label=ClassLabelEnum.TEXT,
            bbox=[10.0, 20.0, 100.0, 50.0],
            confidence=1.0,
            reading_order_index=1,
        )

        # Invalid: out of range
        with pytest.raises(ValidationError):
            LayoutBlock(
                block_id="b001",
                class_label=ClassLabelEnum.TEXT,
                bbox=[10.0, 20.0, 100.0, 50.0],
                confidence=-0.1,
                reading_order_index=1,
            )

        with pytest.raises(ValidationError):
            LayoutBlock(
                block_id="b001",
                class_label=ClassLabelEnum.TEXT,
                bbox=[10.0, 20.0, 100.0, 50.0],
                confidence=1.1,
                reading_order_index=1,
            )


class TestOCREngineOutput:
    """Test OCREngineOutput model."""

    def test_valid_ocr_output_with_confidence(self):
        """Test OCR output with text and confidence."""
        output = OCREngineOutput(text="This is a test.", confidence=0.92)
        assert output.text == "This is a test."
        assert output.confidence == 0.92

    def test_valid_ocr_output_without_confidence(self):
        """Test OCR output with text only (confidence optional)."""
        output = OCREngineOutput(text="This is a test.")
        assert output.text == "This is a test."
        assert output.confidence is None


class TestOCREnginesResult:
    """Test OCREnginesResult model."""

    def test_valid_ocr_engines_result_marker_only(self):
        """Test OCR engines result with only Marker (required)."""
        result = OCREnginesResult(
            marker=OCREngineOutput(text="Marker text", confidence=0.95)
        )
        assert result.marker.text == "Marker text"
        assert result.deepseek_ocr is None

    def test_valid_ocr_engines_result_both_engines(self):
        """Test OCR engines result with both Marker and DeepSeek-OCR."""
        result = OCREnginesResult(
            marker=OCREngineOutput(text="Marker text", confidence=0.95),
            deepseek_ocr=OCREngineOutput(text="DeepSeek text", confidence=0.88),
        )
        assert result.marker.text == "Marker text"
        assert result.deepseek_ocr.text == "DeepSeek text"

    def test_marker_required(self):
        """Test Marker OCR output is required."""
        with pytest.raises(ValidationError):
            OCREnginesResult(
                deepseek_ocr=OCREngineOutput(text="DeepSeek only")
            )  # Missing required marker


class TestParagraph:
    """Test Paragraph model."""

    def test_valid_paragraph_minimal(self):
        """Test minimal valid paragraph."""
        para = Paragraph(
            paragraph_id="p001",
            page_index=0,
            layout_block_id="b001",
            structural_role=StructuralRoleEnum.BODY_TEXT,
            reading_order_index=1,
            ocr_engines=OCREnginesResult(
                marker=OCREngineOutput(text="This is a paragraph.")
            ),
        )
        assert para.paragraph_id == "p001"
        assert para.structural_role == StructuralRoleEnum.BODY_TEXT
        assert para.heading_path == []  # Default empty list

    def test_valid_paragraph_full(self):
        """Test paragraph with all optional fields."""
        para = Paragraph(
            paragraph_id="p001",
            page_index=0,
            layout_block_id="b001",
            heading_path=["Introduction", "Background"],
            structural_role=StructuralRoleEnum.BODY_TEXT,
            reading_order_index=1,
            ocr_engines=OCREnginesResult(
                marker=OCREngineOutput(text="Marker text", confidence=0.92),
                deepseek_ocr=OCREngineOutput(text="DeepSeek text", confidence=0.88),
            ),
            languages=["en"],
            has_math=False,
            has_table_ref=False,
            has_handwriting=False,
        )
        assert para.heading_path == ["Introduction", "Background"]
        assert para.languages == ["en"]
        assert para.has_math is False

    def test_structural_role_enum_validation(self):
        """Test structural_role must be valid enum."""
        # Valid roles
        for role in StructuralRoleEnum:
            Paragraph(
                paragraph_id="p001",
                page_index=0,
                layout_block_id="b001",
                structural_role=role,
                reading_order_index=1,
                ocr_engines=OCREnginesResult(
                    marker=OCREngineOutput(text="Test")
                ),
            )

        # Invalid role
        with pytest.raises(ValidationError):
            Paragraph(
                paragraph_id="p001",
                page_index=0,
                layout_block_id="b001",
                structural_role="invalid_role",
                reading_order_index=1,
                ocr_engines=OCREnginesResult(
                    marker=OCREngineOutput(text="Test")
                ),
            )


class TestOCRPage:
    """Test OCRPage model."""

    def test_valid_ocr_page(self):
        """Test valid OCR page with blocks, reading order, and paragraphs."""
        page = OCRPage(
            page_index=0,
            width_px=595,
            height_px=842,
            layout_blocks=[
                LayoutBlock(
                    block_id="b001",
                    class_label=ClassLabelEnum.TEXT,
                    bbox=[50.0, 100.0, 495.0, 50.0],
                    confidence=0.95,
                    reading_order_index=1,
                ),
                LayoutBlock(
                    block_id="b002",
                    class_label=ClassLabelEnum.TABLE,
                    bbox=[50.0, 200.0, 495.0, 150.0],
                    confidence=0.92,
                    reading_order_index=2,
                ),
            ],
            reading_order=["b001", "b002"],
            paragraphs=[
                Paragraph(
                    paragraph_id="p001",
                    page_index=0,
                    layout_block_id="b001",
                    structural_role=StructuralRoleEnum.BODY_TEXT,
                    reading_order_index=1,
                    ocr_engines=OCREnginesResult(
                        marker=OCREngineOutput(text="Paragraph text")
                    ),
                )
            ],
        )
        assert page.page_index == 0
        assert len(page.layout_blocks) == 2
        assert len(page.reading_order) == 2
        assert len(page.paragraphs) == 1

    def test_ocr_page_dimension_validation(self):
        """Test page dimensions must be >= 1."""
        with pytest.raises(ValidationError):
            OCRPage(
                page_index=0,
                width_px=0,  # Invalid
                height_px=842,
                layout_blocks=[],
                reading_order=[],
                paragraphs=[],
            )


class TestOCRDocument:
    """Test OCRDocument main model."""

    def test_valid_ocr_document_minimal(self):
        """Test minimal valid OCRDocument."""
        doc = OCRDocument(
            schema_version="1.0.0",
            document_id="test-doc-001",
            page_count=1,
            layout_model_name="yolov10_doc_v1",
            ocr_engines=["marker"],
            pages=[
                OCRPage(
                    page_index=0,
                    width_px=595,
                    height_px=842,
                    layout_blocks=[
                        LayoutBlock(
                            block_id="b001",
                            class_label=ClassLabelEnum.TEXT,
                            bbox=[50.0, 100.0, 495.0, 50.0],
                            confidence=0.95,
                            reading_order_index=1,
                        )
                    ],
                    reading_order=["b001"],
                    paragraphs=[
                        Paragraph(
                            paragraph_id="p001",
                            page_index=0,
                            layout_block_id="b001",
                            structural_role=StructuralRoleEnum.BODY_TEXT,
                            reading_order_index=1,
                            ocr_engines=OCREnginesResult(
                                marker=OCREngineOutput(text="Test paragraph")
                            ),
                        )
                    ],
                )
            ],
        )
        assert doc.document_id == "test-doc-001"
        assert doc.page_count == 1
        assert len(doc.pages) == 1

    def test_valid_ocr_document_multiple_engines(self):
        """Test OCRDocument with multiple OCR engines."""
        doc = OCRDocument(
            schema_version="1.0.0",
            document_id="test-doc-001",
            source_document_metadata_id="metadata-001",
            page_count=1,
            layout_model_name="yolov10_doc_v1",
            ocr_engines=["marker", "deepseek_ocr"],
            pages=[],
        )
        assert doc.ocr_engines == ["marker", "deepseek_ocr"]
        assert doc.source_document_metadata_id == "metadata-001"

    def test_ocr_document_no_extra_fields(self):
        """Test OCRDocument rejects extra fields."""
        with pytest.raises(ValidationError):
            OCRDocument(
                schema_version="1.0.0",
                document_id="test",
                page_count=1,
                layout_model_name="yolov10_doc_v1",
                ocr_engines=["marker"],
                pages=[],
                extra_field="invalid",  # Should be rejected
            )

    def test_ocr_document_json_serialization(self):
        """Test OCRDocument can serialize to/from JSON."""
        doc = OCRDocument(
            schema_version="1.0.0",
            document_id="test-doc-001",
            page_count=1,
            layout_model_name="yolov10_doc_v1",
            ocr_engines=["marker"],
            pages=[],
        )

        # Serialize to JSON
        json_str = doc.model_dump_json()
        assert "test-doc-001" in json_str
        assert "yolov10_doc_v1" in json_str

        # Deserialize from JSON
        doc2 = OCRDocument.model_validate_json(json_str)
        assert doc2.document_id == doc.document_id
        assert doc2.layout_model_name == doc.layout_model_name
