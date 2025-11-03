"""Format detection utilities for identifying document types."""

import mimetypes
from pathlib import Path
from typing import Any

import magic

from data_ingestor.core.models import DocumentFormat


class FormatDetector:
    """Detect document format using multiple strategies."""

    # MIME type to format mapping
    MIME_TYPE_MAP: dict[str, DocumentFormat] = {
        "application/pdf": DocumentFormat.PDF,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocumentFormat.DOCX,
        "application/msword": DocumentFormat.DOCX,
        "text/html": DocumentFormat.HTML,
        "application/xhtml+xml": DocumentFormat.HTML,
        "video/mp4": DocumentFormat.VIDEO,
        "video/mpeg": DocumentFormat.VIDEO,
        "video/quicktime": DocumentFormat.VIDEO,
        "video/x-msvideo": DocumentFormat.VIDEO,
        "video/x-matroska": DocumentFormat.VIDEO,
        "audio/mpeg": DocumentFormat.AUDIO,
        "audio/wav": DocumentFormat.AUDIO,
        "audio/x-wav": DocumentFormat.AUDIO,
        "audio/ogg": DocumentFormat.AUDIO,
        "audio/mp4": DocumentFormat.AUDIO,
    }

    # File extension to format mapping
    EXTENSION_MAP: dict[str, DocumentFormat] = {
        ".pdf": DocumentFormat.PDF,
        ".docx": DocumentFormat.DOCX,
        ".doc": DocumentFormat.DOCX,
        ".html": DocumentFormat.HTML,
        ".htm": DocumentFormat.HTML,
        ".mp4": DocumentFormat.VIDEO,
        ".avi": DocumentFormat.VIDEO,
        ".mov": DocumentFormat.VIDEO,
        ".mkv": DocumentFormat.VIDEO,
        ".webm": DocumentFormat.VIDEO,
        ".mp3": DocumentFormat.AUDIO,
        ".wav": DocumentFormat.AUDIO,
        ".ogg": DocumentFormat.AUDIO,
        ".m4a": DocumentFormat.AUDIO,
        ".flac": DocumentFormat.AUDIO,
    }

    def __init__(self) -> None:
        """Initialize format detector."""
        # Initialize magic for file type detection
        try:
            self.magic_detector = magic.Magic(mime=True)
        except Exception:
            # #EDGE: Library Availability: python-magic may not be installed correctly
            # #VERIFY: Fall back to mimetypes library if magic fails
            self.magic_detector = None

    def detect_from_path(self, file_path: str | Path) -> DocumentFormat:
        """Detect document format from file path.

        # #CRITICAL: Format Detection: Multi-stage detection prevents misidentification
        # #VERIFY: Should validate detection confidence and allow manual override

        Args:
            file_path: Path to the file

        Returns:
            Detected document format
        """
        path = Path(file_path)

        # Stage 1: Try magic (libmagic) for most accurate detection
        if self.magic_detector:
            try:
                mime_type = self.magic_detector.from_file(str(path))
                format_detected = self.MIME_TYPE_MAP.get(mime_type)
                if format_detected:
                    return format_detected
            except Exception:
                # #EDGE: File Access: File may be inaccessible or corrupted
                # #VERIFY: Log error and continue to fallback methods
                pass

        # Stage 2: Try mimetypes library
        mime_type, _ = mimetypes.guess_type(str(path))
        if mime_type:
            format_detected = self.MIME_TYPE_MAP.get(mime_type)
            if format_detected:
                return format_detected

        # Stage 3: Fall back to file extension
        extension = path.suffix.lower()
        format_detected = self.EXTENSION_MAP.get(extension)
        if format_detected:
            return format_detected

        # #ASSUME: Format Detection: Unknown formats default to UNKNOWN
        # #VERIFY: Should log and potentially flag for manual review
        return DocumentFormat.UNKNOWN

    def detect_from_url(self, url: str) -> DocumentFormat:
        """Detect document format from URL.

        # #EDGE: URL Format: URL-based detection is less reliable than file inspection
        # #VERIFY: Should validate after download

        Args:
            url: URL to analyze

        Returns:
            Detected document format (may be HTML or UNKNOWN)
        """
        url_lower = url.lower()

        # Check for explicit file extensions in URL
        for ext, fmt in self.EXTENSION_MAP.items():
            if url_lower.endswith(ext):
                return fmt

        # Default to HTML for web URLs
        if url_lower.startswith(("http://", "https://")):
            return DocumentFormat.HTML

        return DocumentFormat.UNKNOWN

    def validate_format(self, file_path: str | Path, expected_format: DocumentFormat) -> bool:
        """Validate that file matches expected format.

        Args:
            file_path: Path to the file
            expected_format: Expected document format

        Returns:
            True if format matches, False otherwise
        """
        detected_format = self.detect_from_path(file_path)
        return detected_format == expected_format

    def get_mime_type(self, file_path: str | Path) -> str | None:
        """Get MIME type for file.

        Args:
            file_path: Path to the file

        Returns:
            MIME type string or None if detection fails
        """
        path = Path(file_path)

        if self.magic_detector:
            try:
                return self.magic_detector.from_file(str(path))
            except Exception:
                pass

        mime_type, _ = mimetypes.guess_type(str(path))
        return mime_type

    def get_format_info(self, file_path: str | Path) -> dict[str, Any]:
        """Get comprehensive format information.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with format information
        """
        path = Path(file_path)
        detected_format = self.detect_from_path(path)
        mime_type = self.get_mime_type(path)

        return {
            "format": detected_format,
            "mime_type": mime_type,
            "extension": path.suffix.lower(),
            "file_name": path.name,
            "file_size_bytes": path.stat().st_size if path.exists() else None,
        }
