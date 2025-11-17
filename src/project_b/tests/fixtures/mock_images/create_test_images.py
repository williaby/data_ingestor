"""
Script to create minimal synthetic test images for unit testing.

Creates tiny (100x100 pixel) PNG images for testing image loading
without duplicating real dataset storage.

Real images from Project A are stored in GCS (as specified in DocumentMetadata).
These synthetic images are only for unit tests.
"""

from pathlib import Path

import numpy as np
from PIL import Image


def create_test_images():
    """Create minimal synthetic test images."""
    output_dir = Path(__file__).parent

    # 1. Simple white page (simulates born-digital PDF page)
    white_page = np.ones((100, 100, 3), dtype=np.uint8) * 255
    Image.fromarray(white_page).save(output_dir / "simple_page_white.png")
    print("Created: simple_page_white.png (100x100 white)")

    # 2. Simple with text-like regions (black boxes simulating text)
    text_page = np.ones((100, 100, 3), dtype=np.uint8) * 255
    # Simulate text blocks
    text_page[10:20, 10:80] = 0  # Header region
    text_page[25:30, 10:90] = 0  # Text line 1
    text_page[32:37, 10:85] = 0  # Text line 2
    text_page[39:44, 10:70] = 0  # Text line 3
    Image.fromarray(text_page).save(output_dir / "simple_page_with_text.png")
    print("Created: simple_page_with_text.png (100x100 with text blocks)")

    # 3. Page with table-like structure
    table_page = np.ones((100, 100, 3), dtype=np.uint8) * 255
    # Simulate table grid
    table_page[20:80, 10] = 0  # Left border
    table_page[20:80, 90] = 0  # Right border
    table_page[20, 10:90] = 0  # Top border
    table_page[80, 10:90] = 0  # Bottom border
    table_page[50, 10:90] = 0  # Horizontal divider
    table_page[20:80, 50] = 0  # Vertical divider
    Image.fromarray(table_page).save(output_dir / "page_with_table.png")
    print("Created: page_with_table.png (100x100 with table grid)")

    # 4. Degraded/scanned page (add noise)
    degraded_page = np.ones((100, 100, 3), dtype=np.uint8) * 240  # Slightly gray
    # Add random noise to simulate scan artifacts
    noise = np.random.randint(0, 30, (100, 100, 3), dtype=np.uint8)
    degraded_page = np.clip(degraded_page - noise, 0, 255).astype(np.uint8)
    # Add some text blocks
    degraded_page[10:15, 10:80] = np.random.randint(0, 50, (5, 70, 3))
    degraded_page[20:25, 10:85] = np.random.randint(0, 50, (5, 75, 3))
    Image.fromarray(degraded_page).save(output_dir / "degraded_scan.png")
    print("Created: degraded_scan.png (100x100 with noise and artifacts)")

    # 5. Multi-column page layout
    multicolumn_page = np.ones((100, 100, 3), dtype=np.uint8) * 255
    # Left column
    multicolumn_page[10:90, 5:45] = 200  # Light gray background for column
    multicolumn_page[12:15, 7:43] = 0  # Text lines
    multicolumn_page[17:20, 7:43] = 0
    multicolumn_page[22:25, 7:40] = 0
    # Right column
    multicolumn_page[10:90, 55:95] = 200  # Light gray background for column
    multicolumn_page[12:15, 57:93] = 0  # Text lines
    multicolumn_page[17:20, 57:93] = 0
    multicolumn_page[22:25, 57:90] = 0
    Image.fromarray(multicolumn_page).save(output_dir / "multicolumn_layout.png")
    print("Created: multicolumn_layout.png (100x100 two-column layout)")

    # 6. Page with figure region
    figure_page = np.ones((100, 100, 3), dtype=np.uint8) * 255
    # Figure region (gradient to simulate image)
    for i in range(30, 70):
        figure_page[30:70, i] = [int((i-30) * 6.375), 100, 200]
    # Border around figure
    figure_page[30, 30:70] = 0
    figure_page[69, 30:70] = 0
    figure_page[30:70, 30] = 0
    figure_page[30:70, 69] = 0
    # Caption below
    figure_page[72:75, 30:60] = 0
    Image.fromarray(figure_page).save(output_dir / "page_with_figure.png")
    print("Created: page_with_figure.png (100x100 with figure and caption)")

    # 7. Minimal 1x1 transparent PNG (for mock GCS blob in tests)
    transparent_1x1 = np.array([[[0, 0, 0, 0]]], dtype=np.uint8)
    Image.fromarray(transparent_1x1, mode='RGBA').save(output_dir / "mock_1x1_transparent.png")
    print("Created: mock_1x1_transparent.png (1x1 transparent for mock GCS)")

    print(f"\nCreated 7 synthetic test images in {output_dir}")
    print("These are minimal fixtures for unit testing only.")
    print("Real page images are stored in GCS (see DocumentMetadata.pages[].corrected_image_gcs_path)")


if __name__ == "__main__":
    create_test_images()
