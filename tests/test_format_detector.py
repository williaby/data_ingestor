"""
Comprehensive tests for utils/format_detector.py module.

Tests cover:
- FormatDetector initialization with/without magic library
- Multi-stage format detection (magic, mimetypes, extension)
- URL-based format detection
- Format validation
- MIME type detection
- Comprehensive format information retrieval
- Edge cases and error handling
"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from data_ingestor.core.models import DocumentFormat
from data_ingestor.utils.format_detector import FormatDetector


class TestFormatDetectorInitialization:
    """Test FormatDetector initialization scenarios."""

    def test_initialization_with_magic_success(self):
        """Test successful initialization with python-magic library."""
        with patch("data_ingestor.utils.format_detector.magic.Magic") as mock_magic:
            mock_magic_instance = Mock()
            mock_magic.return_value = mock_magic_instance

            detector = FormatDetector()

            assert detector.magic_detector == mock_magic_instance
            mock_magic.assert_called_once_with(mime=True)

    def test_initialization_magic_library_failure(self):
        """Test initialization when python-magic library fails."""
        with patch(
            "data_ingestor.utils.format_detector.magic.Magic",
            side_effect=Exception("Magic library not available"),
        ):
            detector = FormatDetector()

            assert detector.magic_detector is None


class TestDetectFromPath:
    """Test detect_from_path method with various scenarios."""

    @pytest.fixture
    def mock_pdf_file(self, tmp_path):
        """Create a mock PDF file for testing."""
        pdf_file = tmp_path / "test_document.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake pdf content")
        return pdf_file

    @pytest.fixture
    def mock_docx_file(self, tmp_path):
        """Create a mock DOCX file for testing."""
        docx_file = tmp_path / "test_document.docx"
        docx_file.write_bytes(b"fake docx content")
        return docx_file

    def test_detect_pdf_with_magic_success(self, mock_pdf_file):
        """Test PDF detection using magic library (stage 1)."""
        mock_magic = Mock()
        mock_magic.from_file.return_value = "application/pdf"

        with patch("data_ingestor.utils.format_detector.magic.Magic") as magic_class:
            magic_class.return_value = mock_magic
            detector = FormatDetector()

            result = detector.detect_from_path(mock_pdf_file)

            assert result == DocumentFormat.PDF
            mock_magic.from_file.assert_called_once_with(str(mock_pdf_file))

    def test_detect_docx_with_magic_success(self, mock_docx_file):
        """Test DOCX detection using magic library (stage 1)."""
        mock_magic = Mock()
        mock_magic.from_file.return_value = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        with patch("data_ingestor.utils.format_detector.magic.Magic") as magic_class:
            magic_class.return_value = mock_magic
            detector = FormatDetector()

            result = detector.detect_from_path(mock_docx_file)

            assert result == DocumentFormat.DOCX

    def test_detect_html_with_magic_success(self, tmp_path):
        """Test HTML detection using magic library (stage 1)."""
        html_file = tmp_path / "test.html"
        html_file.write_text("<html><body>Test</body></html>")

        mock_magic = Mock()
        mock_magic.from_file.return_value = "text/html"

        with patch("data_ingestor.utils.format_detector.magic.Magic") as magic_class:
            magic_class.return_value = mock_magic
            detector = FormatDetector()

            result = detector.detect_from_path(html_file)

            assert result == DocumentFormat.HTML

    def test_detect_video_formats(self, tmp_path):
        """Test video format detection using extension fallback."""
        # Test multiple video formats
        video_files = [
            ("test.mp4", DocumentFormat.VIDEO),
            ("test.avi", DocumentFormat.VIDEO),
            ("test.mov", DocumentFormat.VIDEO),
            ("test.mkv", DocumentFormat.VIDEO),
            ("test.webm", DocumentFormat.VIDEO),
        ]

        with patch(
            "data_ingestor.utils.format_detector.magic.Magic",
            side_effect=Exception("Not available"),
        ):
            detector = FormatDetector()

            for filename, expected_format in video_files:
                file_path = tmp_path / filename
                file_path.write_bytes(b"fake video content")

                result = detector.detect_from_path(file_path)
                assert (
                    result == expected_format
                ), f"Failed for {filename}: expected {expected_format}, got {result}"

    def test_detect_audio_formats(self, tmp_path):
        """Test audio format detection using extension fallback."""
        audio_files = [
            ("test.mp3", DocumentFormat.AUDIO),
            ("test.wav", DocumentFormat.AUDIO),
            ("test.ogg", DocumentFormat.AUDIO),
            ("test.m4a", DocumentFormat.AUDIO),
            ("test.flac", DocumentFormat.AUDIO),
        ]

        with patch(
            "data_ingestor.utils.format_detector.magic.Magic",
            side_effect=Exception("Not available"),
        ):
            detector = FormatDetector()

            for filename, expected_format in audio_files:
                file_path = tmp_path / filename
                file_path.write_bytes(b"fake audio content")

                result = detector.detect_from_path(file_path)
                assert result == expected_format, f"Failed for {filename}"

    def test_detect_magic_failure_falls_back_to_mimetypes(self, mock_pdf_file):
        """Test fallback to mimetypes when magic fails (stage 2)."""
        mock_magic = Mock()
        mock_magic.from_file.side_effect = Exception("Magic read error")

        with patch("data_ingestor.utils.format_detector.magic.Magic") as magic_class:
            magic_class.return_value = mock_magic
            with patch("data_ingestor.utils.format_detector.mimetypes.guess_type") as mock_guess:
                mock_guess.return_value = ("application/pdf", None)

                detector = FormatDetector()
                result = detector.detect_from_path(mock_pdf_file)

                assert result == DocumentFormat.PDF
                mock_guess.assert_called_once()

    def test_detect_mimetypes_failure_falls_back_to_extension(self, tmp_path):
        """Test fallback to extension when mimetypes fails (stage 3)."""
        test_file = tmp_path / "document.pdf"
        test_file.write_bytes(b"content")

        with patch(
            "data_ingestor.utils.format_detector.magic.Magic",
            side_effect=Exception("Not available"),
        ):
            with patch(
                "data_ingestor.utils.format_detector.mimetypes.guess_type"
            ) as mock_guess:
                mock_guess.return_value = (None, None)

                detector = FormatDetector()
                result = detector.detect_from_path(test_file)

                # Should fall back to extension detection
                assert result == DocumentFormat.PDF

    def test_detect_unknown_format(self, tmp_path):
        """Test detection of unknown file format."""
        unknown_file = tmp_path / "document.xyz"
        unknown_file.write_bytes(b"unknown content")

        with patch(
            "data_ingestor.utils.format_detector.magic.Magic",
            side_effect=Exception("Not available"),
        ):
            with patch(
                "data_ingestor.utils.format_detector.mimetypes.guess_type"
            ) as mock_guess:
                mock_guess.return_value = (None, None)

                detector = FormatDetector()
                result = detector.detect_from_path(unknown_file)

                assert result == DocumentFormat.UNKNOWN

    def test_detect_magic_returns_unmapped_mime_type(self, tmp_path):
        """Test when magic returns MIME type not in mapping."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("plain text")

        mock_magic = Mock()
        mock_magic.from_file.return_value = "text/plain"  # Not in MIME_TYPE_MAP

        with patch("data_ingestor.utils.format_detector.magic.Magic") as magic_class:
            magic_class.return_value = mock_magic
            with patch(
                "data_ingestor.utils.format_detector.mimetypes.guess_type"
            ) as mock_guess:
                mock_guess.return_value = (None, None)

                detector = FormatDetector()
                result = detector.detect_from_path(test_file)

                # Should fall back to extension or return UNKNOWN
                assert result == DocumentFormat.UNKNOWN

    def test_detect_case_insensitive_extension(self, tmp_path):
        """Test that extension detection is case-insensitive."""
        test_files = [
            "document.PDF",
            "document.Pdf",
            "document.PdF",
        ]

        with patch(
            "data_ingestor.utils.format_detector.magic.Magic",
            side_effect=Exception("Not available"),
        ):
            detector = FormatDetector()

            for filename in test_files:
                file_path = tmp_path / filename
                file_path.write_bytes(b"content")

                result = detector.detect_from_path(file_path)
                assert result == DocumentFormat.PDF, f"Failed for {filename}"


class TestDetectFromURL:
    """Test detect_from_url method."""

    def test_detect_pdf_url(self):
        """Test PDF detection from URL."""
        detector = FormatDetector()

        urls = [
            "https://example.com/document.pdf",
            "http://example.com/files/report.PDF",
        ]

        for url in urls:
            result = detector.detect_from_url(url)
            assert result == DocumentFormat.PDF, f"Failed for {url}"

    def test_detect_url_with_query_params(self):
        """Test URL detection with query parameters (known limitation)."""
        detector = FormatDetector()

        # URLs with query parameters won't match extension-based detection
        # They default to HTML for http/https URLs
        url = "https://domain.com/path/to/file.pdf?param=value"
        result = detector.detect_from_url(url)
        assert result == DocumentFormat.HTML  # Known behavior

    def test_detect_docx_url(self):
        """Test DOCX detection from URL."""
        detector = FormatDetector()

        urls = [
            "https://example.com/document.docx",
            "http://example.com/files/report.doc",
        ]

        for url in urls:
            result = detector.detect_from_url(url)
            assert result == DocumentFormat.DOCX

    def test_detect_video_url(self):
        """Test video detection from URL."""
        detector = FormatDetector()

        urls = [
            "https://example.com/video.mp4",
            "http://example.com/content.avi",
            "https://example.com/movie.mov",
        ]

        for url in urls:
            result = detector.detect_from_url(url)
            assert result == DocumentFormat.VIDEO

    def test_detect_audio_url(self):
        """Test audio detection from URL."""
        detector = FormatDetector()

        urls = [
            "https://example.com/audio.mp3",
            "http://example.com/sound.wav",
            "https://example.com/music.ogg",
        ]

        for url in urls:
            result = detector.detect_from_url(url)
            assert result == DocumentFormat.AUDIO

    def test_detect_html_url(self):
        """Test HTML detection for web URLs without extension."""
        detector = FormatDetector()

        urls = [
            "https://example.com",
            "http://example.com/page",
            "https://example.com/article?id=123",
            "http://subdomain.example.com/path",
        ]

        for url in urls:
            result = detector.detect_from_url(url)
            assert result == DocumentFormat.HTML, f"Failed for {url}"

    def test_detect_unknown_url(self):
        """Test detection for non-HTTP URLs."""
        detector = FormatDetector()

        urls = [
            "ftp://example.com/file.txt",
            "file:///local/path/document",
            "mailto:user@example.com",
            "",
        ]

        for url in urls:
            result = detector.detect_from_url(url)
            assert result == DocumentFormat.UNKNOWN, f"Failed for {url}"

    def test_url_case_insensitivity(self):
        """Test that URL detection is case-insensitive."""
        detector = FormatDetector()

        urls = [
            "HTTPS://EXAMPLE.COM/DOCUMENT.PDF",
            "Http://Example.Com/File.Pdf",
        ]

        for url in urls:
            result = detector.detect_from_url(url)
            assert result == DocumentFormat.PDF


class TestValidateFormat:
    """Test validate_format method."""

    def test_validate_format_match(self, tmp_path):
        """Test validation when format matches."""
        pdf_file = tmp_path / "document.pdf"
        pdf_file.write_bytes(b"content")

        with patch(
            "data_ingestor.utils.format_detector.magic.Magic",
            side_effect=Exception("Not available"),
        ):
            detector = FormatDetector()
            result = detector.validate_format(pdf_file, DocumentFormat.PDF)

            assert result is True

    def test_validate_format_mismatch(self, tmp_path):
        """Test validation when format doesn't match."""
        pdf_file = tmp_path / "document.pdf"
        pdf_file.write_bytes(b"content")

        with patch(
            "data_ingestor.utils.format_detector.magic.Magic",
            side_effect=Exception("Not available"),
        ):
            detector = FormatDetector()
            result = detector.validate_format(pdf_file, DocumentFormat.DOCX)

            assert result is False

    def test_validate_unknown_format(self, tmp_path):
        """Test validation of unknown format."""
        unknown_file = tmp_path / "document.xyz"
        unknown_file.write_bytes(b"content")

        with patch(
            "data_ingestor.utils.format_detector.magic.Magic",
            side_effect=Exception("Not available"),
        ):
            with patch(
                "data_ingestor.utils.format_detector.mimetypes.guess_type"
            ) as mock_guess:
                mock_guess.return_value = (None, None)

                detector = FormatDetector()
                result = detector.validate_format(unknown_file, DocumentFormat.UNKNOWN)

                assert result is True


class TestGetMimeType:
    """Test get_mime_type method."""

    def test_get_mime_type_with_magic(self, tmp_path):
        """Test MIME type retrieval using magic library."""
        pdf_file = tmp_path / "document.pdf"
        pdf_file.write_bytes(b"content")

        mock_magic = Mock()
        mock_magic.from_file.return_value = "application/pdf"

        with patch("data_ingestor.utils.format_detector.magic.Magic") as magic_class:
            magic_class.return_value = mock_magic
            detector = FormatDetector()

            result = detector.get_mime_type(pdf_file)

            assert result == "application/pdf"
            mock_magic.from_file.assert_called_once_with(str(pdf_file))

    def test_get_mime_type_magic_failure_fallback(self, tmp_path):
        """Test MIME type fallback to mimetypes when magic fails."""
        pdf_file = tmp_path / "document.pdf"
        pdf_file.write_bytes(b"content")

        mock_magic = Mock()
        mock_magic.from_file.side_effect = Exception("Read error")

        with patch("data_ingestor.utils.format_detector.magic.Magic") as magic_class:
            magic_class.return_value = mock_magic
            with patch("data_ingestor.utils.format_detector.mimetypes.guess_type") as mock_guess:
                mock_guess.return_value = ("application/pdf", None)

                detector = FormatDetector()
                result = detector.get_mime_type(pdf_file)

                assert result == "application/pdf"

    def test_get_mime_type_no_magic_available(self, tmp_path):
        """Test MIME type retrieval without magic library."""
        pdf_file = tmp_path / "document.pdf"
        pdf_file.write_bytes(b"content")

        with patch(
            "data_ingestor.utils.format_detector.magic.Magic",
            side_effect=Exception("Not available"),
        ):
            with patch("data_ingestor.utils.format_detector.mimetypes.guess_type") as mock_guess:
                mock_guess.return_value = ("application/pdf", None)

                detector = FormatDetector()
                result = detector.get_mime_type(pdf_file)

                assert result == "application/pdf"

    def test_get_mime_type_unknown(self, tmp_path):
        """Test MIME type retrieval for unknown format."""
        unknown_file = tmp_path / "document.xyz"
        unknown_file.write_bytes(b"content")

        with patch(
            "data_ingestor.utils.format_detector.magic.Magic",
            side_effect=Exception("Not available"),
        ):
            with patch(
                "data_ingestor.utils.format_detector.mimetypes.guess_type"
            ) as mock_guess:
                mock_guess.return_value = (None, None)

                detector = FormatDetector()
                result = detector.get_mime_type(unknown_file)

                assert result is None


class TestGetFormatInfo:
    """Test get_format_info method."""

    def test_get_format_info_complete(self, tmp_path):
        """Test comprehensive format information retrieval."""
        pdf_file = tmp_path / "document.pdf"
        pdf_file.write_bytes(b"fake pdf content")

        mock_magic = Mock()
        mock_magic.from_file.return_value = "application/pdf"

        with patch("data_ingestor.utils.format_detector.magic.Magic") as magic_class:
            magic_class.return_value = mock_magic
            detector = FormatDetector()

            info = detector.get_format_info(pdf_file)

            assert info["format"] == DocumentFormat.PDF
            assert info["mime_type"] == "application/pdf"
            assert info["extension"] == ".pdf"
            assert info["file_name"] == "document.pdf"
            assert info["file_size_bytes"] == len(b"fake pdf content")

    def test_get_format_info_nonexistent_file(self, tmp_path):
        """Test format info for nonexistent file."""
        nonexistent = tmp_path / "nonexistent.pdf"

        with patch(
            "data_ingestor.utils.format_detector.magic.Magic",
            side_effect=Exception("Not available"),
        ):
            with patch(
                "data_ingestor.utils.format_detector.mimetypes.guess_type"
            ) as mock_guess:
                mock_guess.return_value = (None, None)

                detector = FormatDetector()
                info = detector.get_format_info(nonexistent)

                assert info["format"] == DocumentFormat.PDF  # From extension
                assert info["file_name"] == "nonexistent.pdf"
                assert info["extension"] == ".pdf"
                assert info["file_size_bytes"] is None  # File doesn't exist

    def test_get_format_info_without_magic(self, tmp_path):
        """Test format info retrieval without magic library."""
        docx_file = tmp_path / "document.docx"
        docx_file.write_bytes(b"fake docx")

        with patch(
            "data_ingestor.utils.format_detector.magic.Magic",
            side_effect=Exception("Not available"),
        ):
            with patch("data_ingestor.utils.format_detector.mimetypes.guess_type") as mock_guess:
                mock_guess.return_value = (
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    None,
                )

                detector = FormatDetector()
                info = detector.get_format_info(docx_file)

                assert info["format"] == DocumentFormat.DOCX
                assert (
                    info["mime_type"]
                    == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                assert info["extension"] == ".docx"
                assert info["file_size_bytes"] == len(b"fake docx")


class TestMIMETypeMapping:
    """Test MIME type to format mapping completeness."""

    def test_mime_type_map_coverage(self):
        """Test that all expected MIME types are mapped."""
        detector = FormatDetector()

        # Test key MIME types
        assert (
            detector.MIME_TYPE_MAP["application/pdf"] == DocumentFormat.PDF
        )
        assert detector.MIME_TYPE_MAP["text/html"] == DocumentFormat.HTML
        assert detector.MIME_TYPE_MAP["video/mp4"] == DocumentFormat.VIDEO
        assert detector.MIME_TYPE_MAP["audio/mpeg"] == DocumentFormat.AUDIO

    def test_extension_map_coverage(self):
        """Test that all expected extensions are mapped."""
        detector = FormatDetector()

        # Test key extensions
        assert detector.EXTENSION_MAP[".pdf"] == DocumentFormat.PDF
        assert detector.EXTENSION_MAP[".docx"] == DocumentFormat.DOCX
        assert detector.EXTENSION_MAP[".html"] == DocumentFormat.HTML
        assert detector.EXTENSION_MAP[".mp4"] == DocumentFormat.VIDEO
        assert detector.EXTENSION_MAP[".mp3"] == DocumentFormat.AUDIO


class TestStringPathHandling:
    """Test handling of string paths vs Path objects."""

    def test_detect_from_string_path(self, tmp_path):
        """Test detection using string path."""
        pdf_file = tmp_path / "document.pdf"
        pdf_file.write_bytes(b"content")

        with patch(
            "data_ingestor.utils.format_detector.magic.Magic",
            side_effect=Exception("Not available"),
        ):
            detector = FormatDetector()
            result = detector.detect_from_path(str(pdf_file))

            assert result == DocumentFormat.PDF

    def test_detect_from_path_object(self, tmp_path):
        """Test detection using Path object."""
        pdf_file = tmp_path / "document.pdf"
        pdf_file.write_bytes(b"content")

        with patch(
            "data_ingestor.utils.format_detector.magic.Magic",
            side_effect=Exception("Not available"),
        ):
            detector = FormatDetector()
            result = detector.detect_from_path(pdf_file)

            assert result == DocumentFormat.PDF

    def test_get_mime_type_string_path(self, tmp_path):
        """Test get_mime_type with string path."""
        pdf_file = tmp_path / "document.pdf"
        pdf_file.write_bytes(b"content")

        with patch(
            "data_ingestor.utils.format_detector.magic.Magic",
            side_effect=Exception("Not available"),
        ):
            with patch("data_ingestor.utils.format_detector.mimetypes.guess_type") as mock_guess:
                mock_guess.return_value = ("application/pdf", None)

                detector = FormatDetector()
                result = detector.get_mime_type(str(pdf_file))

                assert result == "application/pdf"
