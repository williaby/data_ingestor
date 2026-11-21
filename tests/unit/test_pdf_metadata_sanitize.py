"""Unit tests for PDF metadata sanitization (defense against attacker-supplied PDF metadata)."""

import pytest

# These imports require optional heavy deps (fitz etc.) — skip cleanly if absent.
pytest.importorskip("fitz")

from data_ingestor.parsers.pdf_parser import PyMuPDFParser


@pytest.mark.unit
class TestSanitizeMetadataValue:
    sanitize = PyMuPDFParser._sanitize_metadata_value

    def test_passthrough_normal_text(self) -> None:
        assert self.sanitize("Hello world") == "Hello world"

    def test_strips_null_and_control_bytes(self) -> None:
        assert self.sanitize("Hello\x00\x01\x02\x7f world") == "Hello world"

    def test_strips_c1_control_bytes(self) -> None:
        # 0x80-0x9F is the C1 control range; must be stripped too.
        assert self.sanitize("Hello\x80\x9b\x9f world") == "Hello world"

    def test_preserves_printable_above_c1(self) -> None:
        # 0xA0 (non-breaking space) and above are legitimate text — keep them.
        assert self.sanitize("café") == "café"
        assert self.sanitize(" ").strip() == ""  # NBSP is preserved (becomes whitespace)

    def test_preserves_tab_and_newline(self) -> None:
        assert self.sanitize("line1\nline2\tcol") == "line1\nline2\tcol"

    def test_caps_oversized_input(self) -> None:
        result = self.sanitize("a" * 5000)
        assert result.endswith("...[truncated]")
        # Truncated output must never exceed the documented cap.
        assert len(result) == PyMuPDFParser._METADATA_MAX_LEN

    def test_returns_empty_for_non_string(self) -> None:
        assert self.sanitize(None) == ""
        assert self.sanitize(42) == ""
        assert self.sanitize(b"bytes") == ""
