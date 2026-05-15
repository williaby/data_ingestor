"""Unit tests for PDF metadata sanitization (defense against attacker-supplied PDF metadata)."""

import pytest

# These imports require optional heavy deps (fitz etc.) — skip cleanly if absent.
pytest.importorskip("fitz")

from data_ingestor.parsers.pdf_parser import PyMuPDFParser


class TestSanitizeMetadataValue:
    sanitize = PyMuPDFParser._sanitize_metadata_value

    def test_passthrough_normal_text(self) -> None:
        assert self.sanitize("Hello world") == "Hello world"

    def test_strips_null_and_control_bytes(self) -> None:
        assert self.sanitize("Hello\x00\x01\x02\x7f world") == "Hello world"

    def test_preserves_tab_and_newline(self) -> None:
        assert self.sanitize("line1\nline2\tcol") == "line1\nline2\tcol"

    def test_caps_oversized_input(self) -> None:
        result = self.sanitize("a" * 5000)
        assert result.endswith("...[truncated]")
        assert len(result) <= PyMuPDFParser._METADATA_MAX_LEN + len("...[truncated]")

    def test_returns_empty_for_non_string(self) -> None:
        assert self.sanitize(None) == ""
        assert self.sanitize(42) == ""
        assert self.sanitize(b"bytes") == ""
