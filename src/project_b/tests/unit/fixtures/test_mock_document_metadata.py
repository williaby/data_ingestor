"""
Tests for mock DocumentMetadata JSON fixtures.

Validates that mock JSON files in fixtures/mock_documents/ correctly
load and validate against the DocumentMetadata Pydantic model.
"""

import json
from pathlib import Path

import pytest

from project_b.schemas.document_metadata import DocumentMetadata


# Path to mock documents directory
FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "mock_documents"


class TestMockDocumentMetadataFixtures:
    """Test that mock JSON fixtures are valid DocumentMetadata."""

    def test_simple_born_digital_fixture(self):
        """Test simple_born_digital.json loads correctly."""
        fixture_path = FIXTURES_DIR / "simple_born_digital.json"
        assert fixture_path.exists(), f"Fixture not found: {fixture_path}"

        with open(fixture_path) as f:
            data = json.load(f)

        # Validate against Pydantic model
        doc = DocumentMetadata.model_validate(data)

        # Verify key attributes
        assert doc.document_id == "test-simple-001"
        assert doc.document_type.value == "pdf"
        assert doc.pdf_type.value == "born_digital"
        assert doc.page_count == 1
        assert doc.pre_ocr_risk == 0.05
        assert doc.ocr_routing_recommendation.value == "ocr_fast"
        assert len(doc.pages) == 1
        assert len(doc.page_layout_summary) == 1

    def test_complex_multipage_fixture(self):
        """Test complex_multipage.json loads correctly."""
        fixture_path = FIXTURES_DIR / "complex_multipage.json"
        assert fixture_path.exists(), f"Fixture not found: {fixture_path}"

        with open(fixture_path) as f:
            data = json.load(f)

        doc = DocumentMetadata.model_validate(data)

        # Verify key attributes
        assert doc.document_id == "test-complex-001"
        assert doc.pdf_type.value == "hybrid"
        assert doc.page_count == 3
        assert doc.pre_ocr_risk == 0.35
        assert doc.ocr_routing_recommendation.value == "ocr_advanced"
        assert len(doc.pages) == 3
        assert len(doc.page_layout_summary) == 3

        # Verify transform history on page 1 (2 transforms)
        assert len(doc.pages[1].transform_history) == 2
        assert doc.pages[1].transform_history[0].action == "deskew"
        assert doc.pages[1].transform_history[1].action == "clahe"

    def test_scanned_image_only_fixture(self):
        """Test scanned_image_only.json loads correctly."""
        fixture_path = FIXTURES_DIR / "scanned_image_only.json"
        assert fixture_path.exists(), f"Fixture not found: {fixture_path}"

        with open(fixture_path) as f:
            data = json.load(f)

        doc = DocumentMetadata.model_validate(data)

        # Verify key attributes
        assert doc.document_id == "test-scanned-001"
        assert doc.pdf_type.value == "image_only"
        assert doc.page_count == 2
        assert doc.pre_ocr_risk == 0.65
        assert doc.ocr_routing_recommendation.value == "vision_structured"
        assert doc.dqs.degradation_score == 0.55

        # Verify page attributes
        assert doc.page_layout_summary[0].has_handwriting is True
        assert doc.page_layout_summary[0].page_attributes.fuzzy_scan is True

        # Verify skipped transform
        page0_transforms = doc.pages[0].transform_history
        assert any(t.skipped for t in page0_transforms)
        binarize_transform = [t for t in page0_transforms if t.action == "binarize"][0]
        assert binarize_transform.skipped is True
        assert binarize_transform.skip_reason is not None

    def test_office_word_fixture(self):
        """Test office_word.json loads correctly."""
        fixture_path = FIXTURES_DIR / "office_word.json"
        assert fixture_path.exists(), f"Fixture not found: {fixture_path}"

        with open(fixture_path) as f:
            data = json.load(f)

        doc = DocumentMetadata.model_validate(data)

        # Verify key attributes
        assert doc.document_id == "test-office-001"
        assert doc.document_type.value == "office_word"
        assert doc.pdf_type is None  # Office documents have no pdf_type
        assert doc.page_count == 5
        assert doc.pre_ocr_risk == 0.10
        assert doc.dqs.degradation_score == 0.0  # Office docs are pristine

        # Verify pages have minimal processing
        for page in doc.pages:
            assert page.text_detection_confidence == 1.0
            assert len(page.transform_history) == 0  # No transforms for office docs

    def test_all_fixtures_valid(self):
        """Test that all JSON fixtures in mock_documents/ are valid."""
        fixture_files = list(FIXTURES_DIR.glob("*.json"))
        assert len(fixture_files) == 4, "Expected 4 fixture files"

        for fixture_path in fixture_files:
            with open(fixture_path) as f:
                data = json.load(f)

            # Should not raise ValidationError
            doc = DocumentMetadata.model_validate(data)
            assert doc.document_id.startswith("test-")
            assert doc.schema_version == "1.0.0"

    def test_fixture_json_roundtrip(self):
        """Test that fixtures can be serialized back to JSON."""
        fixture_path = FIXTURES_DIR / "simple_born_digital.json"

        with open(fixture_path) as f:
            original_data = json.load(f)

        # Load into Pydantic model
        doc = DocumentMetadata.model_validate(original_data)

        # Serialize back to JSON
        json_str = doc.model_dump_json()
        roundtrip_data = json.loads(json_str)

        # Key fields should match
        assert roundtrip_data["document_id"] == original_data["document_id"]
        assert roundtrip_data["page_count"] == original_data["page_count"]
        assert roundtrip_data["document_type"] == original_data["document_type"]


@pytest.fixture
def simple_document_metadata() -> DocumentMetadata:
    """Fixture that provides a loaded simple DocumentMetadata for tests."""
    fixture_path = FIXTURES_DIR / "simple_born_digital.json"
    with open(fixture_path) as f:
        data = json.load(f)
    return DocumentMetadata.model_validate(data)


@pytest.fixture
def complex_document_metadata() -> DocumentMetadata:
    """Fixture that provides a loaded complex DocumentMetadata for tests."""
    fixture_path = FIXTURES_DIR / "complex_multipage.json"
    with open(fixture_path) as f:
        data = json.load(f)
    return DocumentMetadata.model_validate(data)


@pytest.fixture
def scanned_document_metadata() -> DocumentMetadata:
    """Fixture that provides a loaded scanned DocumentMetadata for tests."""
    fixture_path = FIXTURES_DIR / "scanned_image_only.json"
    with open(fixture_path) as f:
        data = json.load(f)
    return DocumentMetadata.model_validate(data)


@pytest.fixture
def office_document_metadata() -> DocumentMetadata:
    """Fixture that provides a loaded office DocumentMetadata for tests."""
    fixture_path = FIXTURES_DIR / "office_word.json"
    with open(fixture_path) as f:
        data = json.load(f)
    return DocumentMetadata.model_validate(data)
