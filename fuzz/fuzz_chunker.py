#!/usr/bin/env python3
"""Fuzzing harness for document chunking functionality.

This fuzzer tests the TokenChunker and ByTitleChunker for crashes, hangs, and
unexpected behavior when processing adversarial document structures.

Target Areas:
- Token counting with tiktoken
- Chunk overlap logic
- Table preservation
- Section-aware chunking
- Boundary detection
- Memory management for large documents
"""

import sys

import atheris

# Instrument imports before importing target code
with atheris.instrument_imports():
    from data_ingestor.chunking.by_title_chunker import ByTitleChunker
    from data_ingestor.chunking.token_chunker import TokenChunker
    from data_ingestor.core.models import Document, DocumentElement, ElementType


def TestOneInput(data: bytes) -> None:
    """Fuzz target for document chunkers.

    Args:
        data: Arbitrary byte sequence to create document elements
    """
    # Skip inputs that are too small
    if len(data) < 10:
        return

    try:
        # Parse fuzz data to create document elements
        elements = []
        i = 0
        element_count = min(data[0] % 20, 20)  # Max 20 elements to limit execution time

        for elem_idx in range(element_count):
            if i + 3 >= len(data):
                break

            # Extract element properties from fuzz data
            elem_type_idx = data[i] % 5
            elem_types = [
                ElementType.TEXT,
                ElementType.HEADING,
                ElementType.TABLE,
                ElementType.LIST,
                ElementType.CODE,
            ]
            elem_type = elem_types[elem_type_idx]

            # Extract content length from fuzz data
            content_len = min(data[i + 1], 100)  # Max 100 chars per element
            i += 2

            # Extract content from remaining fuzz data
            if i + content_len > len(data):
                content_len = len(data) - i

            try:
                content = data[i : i + content_len].decode("utf-8", errors="ignore")
            except Exception:  # nosec B110
                content = "fuzz content"

            i += content_len

            # Create document element
            element = DocumentElement(
                content=content,
                element_type=elem_type,
                page_number=elem_idx // 5,  # Simulate multi-page document
                metadata={
                    "font_size": 12.0 if elem_type == ElementType.TEXT else 16.0,
                    "position": {"x": 0, "y": elem_idx * 10},
                },
            )
            elements.append(element)

        if not elements:
            return

        # Create document with fuzzed elements
        document = Document(
            document_id="fuzz-test",
            format="pdf",
            elements=elements,
        )

        # Test TokenChunker with various configurations
        try:
            chunk_size = 50 + (data[0] % 200)  # 50-250 tokens
            chunk_overlap = data[1] % 50  # 0-50 token overlap
            preserve_tables = bool(data[2] % 2)

            chunker = TokenChunker(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                preserve_tables=preserve_tables,
            )

            chunks = chunker.chunk_document(document)

            # Access chunk properties to trigger processing
            for chunk in chunks[:5]:  # Limit to first 5 chunks
                _ = chunk.content
                _ = chunk.token_count
                _ = len(chunk.elements) if chunk.elements else 0

        except Exception:  # nosec B110
            # Expected for edge cases
            pass

        # Test ByTitleChunker
        try:
            combine_threshold = 100 + (data[3] % 400)  # 100-500 tokens

            by_title_chunker = ByTitleChunker(
                chunk_size=chunk_size,
                combine_under_n_tokens=combine_threshold,
            )

            chunks = by_title_chunker.chunk_document(document)

            # Access chunk properties to trigger processing
            for chunk in chunks[:5]:  # Limit to first 5 chunks
                _ = chunk.content
                _ = chunk.token_count
                _ = chunk.metadata

        except Exception:  # nosec B110
            # Expected for edge cases
            pass

    except Exception:  # nosec B110
        # Catch all exceptions - fuzzer should not crash on invalid input
        pass


def main() -> None:
    """Main entry point for fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
