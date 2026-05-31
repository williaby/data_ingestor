#!/usr/bin/env python3
"""Fuzzing harness for DocumentRouter functionality.

This fuzzer tests the DocumentRouter for crashes, hangs, and unexpected behavior
when processing various file types and edge cases.

Target Areas:
- Format detection (libmagic, mimetypes, extension fallback)
- Parser selection and fallback chains
- Deduplication logic
- Error handling for unsupported formats
- Hash computation for various inputs
"""

import sys
import tempfile
from pathlib import Path

import atheris

# Instrument imports before importing target code
with atheris.instrument_imports():
    from data_ingestor.core.models import Document
    from data_ingestor.parsers.pdf_parser import PyMuPDFParser
    from data_ingestor.pipeline.router import DocumentRouter, ParserRegistry


def TestOneInput(data: bytes) -> None:
    """Fuzz target for DocumentRouter.

    Args:
        data (bytes): Arbitrary byte sequence to use as file input.
    """
    # Skip inputs that are too small
    if len(data) < 4:
        return

    # Extract file extension hint from first 2 bytes (modulo common extensions)
    extensions = [".pdf", ".docx", ".html", ".txt", ".xml", ".json", ".md"]
    ext_idx = data[0] % len(extensions)
    extension = extensions[ext_idx]

    try:
        # Create temporary file with fuzzed data
        with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            tmp_file.write(data)

        try:
            # Initialize router with PDF parser
            registry = ParserRegistry()
            pdf_parser = PyMuPDFParser()
            registry.register(pdf_parser, [pdf_parser.supports_format])

            router = DocumentRouter(parser_registry=registry)

            # Test format detection
            try:
                detected_format = router._detect_format(tmp_path)
                _ = detected_format.value if detected_format else None
            except Exception:  # nosec B110
                pass

            # Test deduplication hash computation
            try:
                file_hash = router._compute_hash(tmp_path)
                _ = len(file_hash)
            except Exception:  # nosec B110
                pass

            # Test document processing (most likely to trigger crashes)
            try:
                result = router.process_document(tmp_path)
                if result:
                    _ = result.status
                    _ = len(result.elements) if result.elements else 0
            except Exception:  # nosec B110
                # Expected for unsupported formats and malformed inputs
                pass

        finally:
            # Clean up temporary file
            if tmp_path.exists():
                tmp_path.unlink()

    except Exception:  # nosec B110
        # Catch all exceptions - fuzzer should not crash on invalid input
        pass


def main() -> None:
    """Main entry point for fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
