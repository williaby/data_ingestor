#!/usr/bin/env python3
"""Fuzzing harness for PDF parser functionality.

This fuzzer tests the PyMuPDF-based parsers for crashes, hangs, and unexpected
behavior when processing malformed or adversarial PDF inputs.

Target Areas:
- PDF parsing and validation
- Text extraction
- Metadata extraction
- Block processing
- Error handling for corrupted/malformed PDFs
- Memory management for large PDFs
"""

import sys
import tempfile
from pathlib import Path

import atheris

# Instrument imports before importing target code
with atheris.instrument_imports():
    from data_ingestor.core.models import Document, DocumentFormat
    from data_ingestor.parsers.pdf_parser import PyMuPDFParser


def TestOneInput(data: bytes) -> None:
    """Fuzz target for PDF parsing.

    Args:
        data: Arbitrary byte sequence to use as PDF input
    """
    # Skip inputs that are too small to be valid PDFs
    if len(data) < 10:
        return

    try:
        # Create temporary file for PDF data
        # PyMuPDFParser.parse() requires a file path
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            tmp_file.write(data)

        try:
            # Create Document model
            document = Document(
                document_id="fuzz-test",
                format=DocumentFormat.PDF,
                source_path=tmp_path,
            )

            # Test PyMuPDF parser
            parser = PyMuPDFParser()

            # Parse document (this is where crashes/hangs would occur)
            result = parser.parse(document)

            # Access result properties to trigger processing
            if result.elements:
                for element in result.elements[:5]:  # Limit to first 5 elements
                    _ = element.content
                    _ = element.element_type
                    _ = element.page_number

            # Access metadata to trigger processing
            if result.metadata:
                _ = result.metadata.get("page_count")
                _ = result.metadata.get("author")

        finally:
            # Clean up temporary file
            if tmp_path.exists():
                tmp_path.unlink()

    except Exception:  # nosec B110
        # Catch all exceptions - fuzzer should not crash on invalid input
        # Fuzzing requires handling all edge cases without propagating exceptions
        pass


def main() -> None:
    """Main entry point for fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
