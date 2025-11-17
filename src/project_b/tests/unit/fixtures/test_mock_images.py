"""
Tests for mock image fixtures.

Validates that synthetic test images in fixtures/mock_images/ can be loaded
and have the expected properties.
"""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image


# Path to mock images directory
MOCK_IMAGES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "mock_images"


class TestMockImageFixtures:
    """Test that mock image fixtures load correctly."""

    def test_simple_page_white(self):
        """Test simple white page loads correctly."""
        image_path = MOCK_IMAGES_DIR / "simple_page_white.png"
        assert image_path.exists(), f"Image not found: {image_path}"

        img = Image.open(image_path)
        assert img.size == (100, 100)
        assert img.mode == "RGB"

        # Should be white (255, 255, 255)
        img_array = np.array(img)
        assert img_array.shape == (100, 100, 3)
        assert np.all(img_array == 255)

    def test_simple_page_with_text(self):
        """Test page with text blocks loads correctly."""
        image_path = MOCK_IMAGES_DIR / "simple_page_with_text.png"
        assert image_path.exists()

        img = Image.open(image_path)
        assert img.size == (100, 100)
        assert img.mode == "RGB"

        # Should have both white and black pixels
        img_array = np.array(img)
        assert np.any(img_array == 0)  # Has black pixels (text)
        assert np.any(img_array == 255)  # Has white pixels (background)

    def test_page_with_table(self):
        """Test page with table structure loads correctly."""
        image_path = MOCK_IMAGES_DIR / "page_with_table.png"
        assert image_path.exists()

        img = Image.open(image_path)
        assert img.size == (100, 100)
        assert img.mode == "RGB"

        # Should have table borders (black pixels)
        img_array = np.array(img)
        assert np.any(img_array == 0)

    def test_degraded_scan(self):
        """Test degraded scan with noise loads correctly."""
        image_path = MOCK_IMAGES_DIR / "degraded_scan.png"
        assert image_path.exists()

        img = Image.open(image_path)
        assert img.size == (100, 100)
        assert img.mode == "RGB"

        # Should have variation (noise)
        img_array = np.array(img)
        # Check that not all pixels are the same (has noise)
        unique_values = np.unique(img_array)
        assert len(unique_values) > 10  # Should have many different values due to noise

    def test_multicolumn_layout(self):
        """Test multi-column layout loads correctly."""
        image_path = MOCK_IMAGES_DIR / "multicolumn_layout.png"
        assert image_path.exists()

        img = Image.open(image_path)
        assert img.size == (100, 100)
        assert img.mode == "RGB"

    def test_page_with_figure(self):
        """Test page with figure region loads correctly."""
        image_path = MOCK_IMAGES_DIR / "page_with_figure.png"
        assert image_path.exists()

        img = Image.open(image_path)
        assert img.size == (100, 100)
        assert img.mode == "RGB"

        # Should have colored pixels (gradient in figure)
        img_array = np.array(img)
        assert np.any(img_array[:, :, 0] != 255)  # Not all white in red channel

    def test_mock_1x1_transparent(self):
        """Test 1x1 transparent PNG for mock GCS blob."""
        image_path = MOCK_IMAGES_DIR / "mock_1x1_transparent.png"
        assert image_path.exists()

        img = Image.open(image_path)
        assert img.size == (1, 1)
        assert img.mode == "RGBA"  # Has alpha channel

    def test_all_expected_images_exist(self):
        """Test that all expected synthetic images exist."""
        expected_images = [
            "simple_page_white.png",
            "simple_page_with_text.png",
            "page_with_table.png",
            "degraded_scan.png",
            "multicolumn_layout.png",
            "page_with_figure.png",
            "mock_1x1_transparent.png",
        ]

        for image_name in expected_images:
            image_path = MOCK_IMAGES_DIR / image_name
            assert image_path.exists(), f"Missing expected image: {image_name}"

    def test_images_are_small_fixtures(self):
        """Test that images are small (not real dataset images)."""
        # All images should be <= 100x100 (except 1x1 transparent)
        # This ensures we're not storing large real images
        for image_path in MOCK_IMAGES_DIR.glob("*.png"):
            if image_path.name == "create_test_images.py":
                continue

            img = Image.open(image_path)
            width, height = img.size
            assert width <= 100 and height <= 100, (
                f"{image_path.name} is too large ({width}x{height}). "
                f"Use GCS paths for real images!"
            )


@pytest.fixture
def simple_white_image() -> Image.Image:
    """Fixture that provides a loaded simple white image for tests."""
    image_path = MOCK_IMAGES_DIR / "simple_page_white.png"
    return Image.open(image_path)


@pytest.fixture
def text_page_image() -> Image.Image:
    """Fixture that provides a loaded page with text for tests."""
    image_path = MOCK_IMAGES_DIR / "simple_page_with_text.png"
    return Image.open(image_path)


@pytest.fixture
def table_page_image() -> Image.Image:
    """Fixture that provides a loaded page with table for tests."""
    image_path = MOCK_IMAGES_DIR / "page_with_table.png"
    return Image.open(image_path)


@pytest.fixture
def degraded_scan_image() -> Image.Image:
    """Fixture that provides a loaded degraded scan for tests."""
    image_path = MOCK_IMAGES_DIR / "degraded_scan.png"
    return Image.open(image_path)
