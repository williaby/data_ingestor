"""
Pytest configuration and shared fixtures for Project B tests.

This module provides shared fixtures and configuration for all test levels:
- Unit tests: Isolated component testing with mocks
- Component tests: Multi-component integration with mocked external dependencies
- Integration tests: End-to-end flows with real dependencies
- E2E tests: Full pipeline testing with real models and data
"""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest


@pytest.fixture
def tmp_dir() -> Path:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_document_metadata() -> Dict[str, Any]:
    """Provide sample DocumentMetadata JSON for testing."""
    return {
        "document_id": "test-doc-001",
        "source_path": "gs://test-bucket/documents/sample.pdf",
        "pdf_type": "digital_native",
        "dqs": {
            "degradation_score": 0.05,
            "structural_complexity_score": 0.60,
            "overall_quality": "high"
        },
        "ocr_routing_recommendation": "marker_llama4",
        "page_layout_summary": {
            "dominant_layout": "single_column",
            "has_tables": True,
            "has_formulas": False,
            "has_images": True
        },
        "pages": [
            {
                "page_number": 1,
                "corrected_image_gcs_path": "gs://test-bucket/corrected/sample_page_001.png",
                "width": 595,
                "height": 842,
                "dpi": 300,
                "degradation_level": "none"
            }
        ]
    }


@pytest.fixture
def sample_ocr_document() -> Dict[str, Any]:
    """Provide sample OCRDocument JSON for testing."""
    return {
        "document_id": "test-doc-001",
        "layout_model_name": "yolov10_doc_v1",
        "layout_model_version": "1.0.0",
        "ocr_engines": ["marker", "deepseek_ocr"],
        "processing_timestamp": "2025-11-17T10:30:00Z",
        "pages": [
            {
                "page_number": 1,
                "layout_blocks": [
                    {
                        "block_id": "b001",
                        "class_label": "text",
                        "bbox": [50, 100, 495, 50],
                        "confidence": 0.95,
                        "reading_order_index": 1
                    }
                ],
                "reading_order": ["b001"],
                "paragraphs": [
                    {
                        "paragraph_id": "p001",
                        "block_ids": ["b001"],
                        "heading_path": ["Introduction"],
                        "structural_role": "body_text",
                        "ocr_engines": {
                            "marker": {
                                "text": "This is a sample paragraph.",
                                "confidence": 0.92
                            }
                        }
                    }
                ]
            }
        ]
    }


@pytest.fixture
def sample_layout_block() -> Dict[str, Any]:
    """Provide sample layout block for testing."""
    return {
        "block_id": "b001",
        "class_label": "text",
        "bbox": [50, 100, 495, 50],  # [x, y, width, height] in COCO format
        "confidence": 0.95,
        "reading_order_index": 1
    }


@pytest.fixture
def mock_gcs_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock Google Cloud Storage client for testing."""
    class MockBlob:
        def __init__(self, name: str):
            self.name = name

        def download_as_bytes(self) -> bytes:
            # Return a minimal valid PNG image (1x1 transparent pixel)
            return (
                b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
                b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
                b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
                b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
            )

    class MockBucket:
        def blob(self, name: str) -> MockBlob:
            return MockBlob(name)

    class MockStorageClient:
        def bucket(self, name: str) -> MockBucket:
            return MockBucket()

    # Mock the storage client import
    monkeypatch.setattr(
        "google.cloud.storage.Client",
        lambda: MockStorageClient()
    )


@pytest.fixture
def mock_yolov10_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock YOLOv10 model for layout detection testing."""
    class MockResults:
        def __init__(self):
            self.boxes = type('obj', (object,), {
                'xyxy': [[50, 100, 545, 150]],  # [x1, y1, x2, y2]
                'conf': [0.95],
                'cls': [0]  # Class 0 = text
            })()

    class MockModel:
        def __call__(self, image, **kwargs):
            return [MockResults()]

    monkeypatch.setattr(
        "ultralytics.YOLO",
        lambda path: MockModel()
    )


# Pytest configuration hooks
def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom settings."""
    # Register custom markers
    config.addinivalue_line(
        "markers", "unit: Unit-level tests (fast, isolated)"
    )
    config.addinivalue_line(
        "markers", "component: Component-level tests (mocked dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (real dependencies)"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests (full pipeline)"
    )
    config.addinivalue_line(
        "markers", "slow: Slow tests (excluded from CI)"
    )
    config.addinivalue_line(
        "markers", "gpu: Tests requiring GPU (excluded when GPU unavailable)"
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Modify test collection to add markers based on path."""
    for item in items:
        # Add markers based on test path
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "component" in str(item.fspath):
            item.add_marker(pytest.mark.component)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
