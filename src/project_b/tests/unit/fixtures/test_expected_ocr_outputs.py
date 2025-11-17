"""
Tests for expected OCRDocument JSON fixtures.

Validates that expected output JSON files in fixtures/expected_outputs/ can be loaded
and conform to the OCRDocument Pydantic schema.
"""

import json
from pathlib import Path

import pytest

from project_b.schemas.ocr_document import OCRDocument


# Path to expected outputs directory
EXPECTED_OUTPUTS_DIR = (
    Path(__file__).parent.parent.parent / "fixtures" / "expected_outputs"
)


class TestExpectedOCROutputFixtures:
    """Test that expected OCRDocument output fixtures load correctly."""

    def test_simple_born_digital_output(self):
        """Test simple born-digital PDF output fixture."""
        fixture_path = EXPECTED_OUTPUTS_DIR / "simple_born_digital_output.json"
        assert fixture_path.exists(), f"Fixture not found: {fixture_path}"

        with open(fixture_path) as f:
            data = json.load(f)

        doc = OCRDocument.model_validate(data)

        # Verify basic properties
        assert doc.document_id == "test-simple-001"
        assert doc.page_count == 1
        assert doc.schema_version == "1.0.0"
        assert doc.layout_model_name == "yolov10x-doclaynet"
        assert "marker" in doc.ocr_engines

        # Verify page structure
        assert len(doc.pages) == 1
        page = doc.pages[0]
        assert page.page_index == 0  # 0-based indexing
        assert len(page.layout_blocks) == 5  # title, text, header, text, footer

        # Verify layout blocks have correct properties
        title_block = page.layout_blocks[0]
        assert title_block.class_label.value == "title"
        assert title_block.confidence >= 0.9
        assert title_block.reading_order_index == 0

        # Verify paragraphs
        assert len(page.paragraphs) == 5
        first_para = page.paragraphs[0]
        assert first_para.paragraph_id == "para_0_0"
        assert first_para.page_index == 0
        assert first_para.ocr_engines.marker is not None
        assert first_para.ocr_engines.marker.text == "Sample Document Title"

    def test_complex_multipage_output(self):
        """Test complex multi-page PDF output fixture."""
        fixture_path = EXPECTED_OUTPUTS_DIR / "complex_multipage_output.json"
        assert fixture_path.exists()

        with open(fixture_path) as f:
            data = json.load(f)

        doc = OCRDocument.model_validate(data)

        # Verify basic properties
        assert doc.document_id == "test-complex-002"
        assert doc.page_count == 3
        assert "marker" in doc.ocr_engines
        assert "deepseek_ocr" in doc.ocr_engines  # Multi-engine consensus

        # Verify all pages present
        assert len(doc.pages) == 3

        # Page 0: Contains table
        page0 = doc.pages[0]
        assert page0.page_index == 0
        table_blocks = [b for b in page0.layout_blocks if b.class_label.value == "table"]
        assert len(table_blocks) > 0, "Page 0 should contain table blocks"

        # Page 1: Contains figure
        page1 = doc.pages[1]
        assert page1.page_index == 1
        figure_blocks = [
            b for b in page1.layout_blocks if b.class_label.value == "picture"
        ]
        assert len(figure_blocks) > 0, "Page 1 should contain figure blocks"

        # Page 2: Contains list items
        page2 = doc.pages[2]
        assert page2.page_index == 2
        list_blocks = [
            b for b in page2.layout_blocks if b.class_label.value == "list_item"
        ]
        assert len(list_blocks) > 0, "Page 2 should contain list blocks"

        # Verify multi-engine OCR results on page 0
        first_para = page0.paragraphs[0]
        assert first_para.ocr_engines.marker is not None
        assert first_para.ocr_engines.deepseek_ocr is not None

    def test_scanned_image_only_output(self):
        """Test scanned image-only PDF output fixture."""
        fixture_path = EXPECTED_OUTPUTS_DIR / "scanned_image_only_output.json"
        assert fixture_path.exists()

        with open(fixture_path) as f:
            data = json.load(f)

        doc = OCRDocument.model_validate(data)

        # Verify basic properties
        assert doc.document_id == "test-scanned-003"
        assert doc.page_count == 2
        assert "marker" in doc.ocr_engines
        assert "deepseek_ocr" in doc.ocr_engines

        # Verify pages
        assert len(doc.pages) == 2

        # Page 0: Should have handwriting block
        page0 = doc.pages[0]
        assert page0.page_index == 0
        handwriting_blocks = [
            b for b in page0.layout_blocks if b.class_label.value == "handwriting"
        ]
        assert len(handwriting_blocks) > 0, "Page 0 should contain handwriting blocks"

        # Verify handwriting paragraph flag
        handwriting_paras = [p for p in page0.paragraphs if p.has_handwriting]
        assert len(handwriting_paras) > 0, "Should have paragraphs marked with handwriting"

        # Page 1: Should have revision marking
        page1 = doc.pages[1]
        assert page1.page_index == 1
        revision_blocks = [
            b for b in page1.layout_blocks if b.class_label.value == "revision_marking"
        ]
        assert len(revision_blocks) > 0, "Page 1 should contain revision marking blocks"

        # Verify lower confidence scores (typical for scanned documents)
        # All paragraphs on page 0 should have marker OCR results
        for para in page0.paragraphs:
            assert para.ocr_engines.marker is not None
            # Scanned docs typically have lower confidence
            assert para.ocr_engines.marker.confidence < 0.85

    def test_office_word_output(self):
        """Test Office Word document output fixture."""
        fixture_path = EXPECTED_OUTPUTS_DIR / "office_word_output.json"
        assert fixture_path.exists()

        with open(fixture_path) as f:
            data = json.load(f)

        doc = OCRDocument.model_validate(data)

        # Verify basic properties
        assert doc.document_id == "test-office-004"
        assert doc.page_count == 5
        assert doc.layout_model_name == "docling-layout-analyzer"  # Office formats
        assert "marker" in doc.ocr_engines

        # Verify all 5 pages
        assert len(doc.pages) == 5

        # Page 0: Title page
        page0 = doc.pages[0]
        assert page0.page_index == 0
        title_blocks = [b for b in page0.layout_blocks if b.class_label.value == "title"]
        assert len(title_blocks) > 0, "Page 0 should be title page"

        # Page 2: Contains table (technology stack)
        page2 = doc.pages[2]
        assert page2.page_index == 2
        table_blocks = [b for b in page2.layout_blocks if b.class_label.value == "table"]
        assert len(table_blocks) > 0, "Page 2 should contain table"

        # Verify high confidence (office documents have clean text)
        for para in page0.paragraphs:
            assert para.ocr_engines.marker is not None
            assert para.ocr_engines.marker.confidence >= 0.95, "Office docs should have high confidence"

        # Verify no DeepSeek-OCR (not needed for office formats)
        assert (
            len(doc.ocr_engines) == 1
        ), "Office docs should only use single engine (no OCR needed)"

    def test_all_expected_outputs_exist(self):
        """Test that all expected output files exist."""
        expected_files = [
            "simple_born_digital_output.json",
            "complex_multipage_output.json",
            "scanned_image_only_output.json",
            "office_word_output.json",
        ]

        for filename in expected_files:
            filepath = EXPECTED_OUTPUTS_DIR / filename
            assert filepath.exists(), f"Missing expected output: {filename}"

    def test_reading_order_consistency(self):
        """Test that all documents have consistent reading order indices."""
        expected_files = [
            "simple_born_digital_output.json",
            "complex_multipage_output.json",
            "scanned_image_only_output.json",
            "office_word_output.json",
        ]

        for filename in expected_files:
            filepath = EXPECTED_OUTPUTS_DIR / filename
            with open(filepath) as f:
                data = json.load(f)

            doc = OCRDocument.model_validate(data)

            for page in doc.pages:
                # Extract reading order indices from layout blocks
                reading_orders = [block.reading_order_index for block in page.layout_blocks]

                # Should start at 0
                assert min(reading_orders) == 0, (
                    f"{filename} page {page.page_index}: "
                    f"Reading order should start at 0"
                )

                # Should be consecutive
                expected_orders = list(range(len(reading_orders)))
                assert sorted(reading_orders) == expected_orders, (
                    f"{filename} page {page.page_index}: "
                    f"Reading order should be consecutive integers starting from 0"
                )

    def test_paragraph_block_association(self):
        """Test that paragraphs are properly associated with layout blocks."""
        fixture_path = EXPECTED_OUTPUTS_DIR / "simple_born_digital_output.json"

        with open(fixture_path) as f:
            data = json.load(f)

        doc = OCRDocument.model_validate(data)
        page = doc.pages[0]

        # Get all block IDs from layout blocks
        layout_block_ids = {block.block_id for block in page.layout_blocks}

        # Verify all paragraphs reference valid block IDs
        for para in page.paragraphs:
            assert para.layout_block_id in layout_block_ids, (
                f"Paragraph {para.paragraph_id} references "
                f"non-existent block: {para.layout_block_id}"
            )

    def test_page_indices_are_zero_based(self):
        """Test that all page indices are 0-based."""
        expected_files = [
            "simple_born_digital_output.json",
            "complex_multipage_output.json",
            "scanned_image_only_output.json",
            "office_word_output.json",
        ]

        for filename in expected_files:
            filepath = EXPECTED_OUTPUTS_DIR / filename
            with open(filepath) as f:
                data = json.load(f)

            doc = OCRDocument.model_validate(data)

            # Verify page indices start at 0 and are consecutive
            page_indices = [page.page_index for page in doc.pages]
            expected_indices = list(range(doc.page_count))
            assert page_indices == expected_indices, (
                f"{filename}: Page indices should be 0-based and consecutive"
            )

    def test_ocr_engines_match_schema(self):
        """Test that OCR engine names match the schema (marker, deepseek_ocr)."""
        fixture_path = EXPECTED_OUTPUTS_DIR / "complex_multipage_output.json"

        with open(fixture_path) as f:
            data = json.load(f)

        doc = OCRDocument.model_validate(data)

        # Verify document-level OCR engines list
        assert "marker" in doc.ocr_engines
        assert "deepseek_ocr" in doc.ocr_engines

        # Verify paragraph-level OCR engines
        page0 = doc.pages[0]
        first_para = page0.paragraphs[0]

        # Both engines should be present in first paragraph
        assert first_para.ocr_engines.marker is not None
        assert first_para.ocr_engines.deepseek_ocr is not None


@pytest.fixture
def simple_born_digital_ocr() -> OCRDocument:
    """Fixture that provides loaded simple born-digital OCR document."""
    fixture_path = EXPECTED_OUTPUTS_DIR / "simple_born_digital_output.json"
    with open(fixture_path) as f:
        data = json.load(f)
    return OCRDocument.model_validate(data)


@pytest.fixture
def complex_multipage_ocr() -> OCRDocument:
    """Fixture that provides loaded complex multi-page OCR document."""
    fixture_path = EXPECTED_OUTPUTS_DIR / "complex_multipage_output.json"
    with open(fixture_path) as f:
        data = json.load(f)
    return OCRDocument.model_validate(data)


@pytest.fixture
def scanned_image_ocr() -> OCRDocument:
    """Fixture that provides loaded scanned image OCR document."""
    fixture_path = EXPECTED_OUTPUTS_DIR / "scanned_image_only_output.json"
    with open(fixture_path) as f:
        data = json.load(f)
    return OCRDocument.model_validate(data)


@pytest.fixture
def office_word_ocr() -> OCRDocument:
    """Fixture that provides loaded Office Word OCR document."""
    fixture_path = EXPECTED_OUTPUTS_DIR / "office_word_output.json"
    with open(fixture_path) as f:
        data = json.load(f)
    return OCRDocument.model_validate(data)
