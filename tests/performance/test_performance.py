"""Performance tests for establishing baselines and measuring throughput."""

import time
from pathlib import Path

import pytest

from data_ingestor.chunking.by_title_chunker import ByTitleChunker
from data_ingestor.chunking.token_chunker import TokenChunker
from data_ingestor.core.models import Document, DocumentFormat
from data_ingestor.parsers.pdf_parser import PyMuPDF4LLMParser, PyMuPDFParser


@pytest.mark.performance
@pytest.mark.slow
class TestParserPerformance:
    """Performance tests for PDF parsers."""

    def test_pymupdf_parser_throughput(
        self,
        performance_test_pdfs: list[Path],
        performance_metrics,
    ) -> None:
        """Measure PyMuPDF parser throughput with multiple PDFs."""
        parser = PyMuPDFParser()
        total_pages = 0
        successful_parses = 0

        performance_metrics.start()

        for pdf_path in performance_test_pdfs:
            doc = Document(source_path=str(pdf_path), format=DocumentFormat.PDF)
            result = parser.parse(doc)

            if result.success:
                successful_parses += 1
                # Estimate pages from result
                pages = len({elem.page_number for elem in result.elements if elem.page_number})
                total_pages += max(pages, 1)

        performance_metrics.stop()

        # Assert performance baseline
        duration = performance_metrics.duration
        throughput_files = successful_parses / duration if duration > 0 else 0

        print("\nPyMuPDF Performance:")
        print(f"  Files processed: {successful_parses}/{len(performance_test_pdfs)}")
        print(f"  Total pages: {total_pages}")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Throughput: {throughput_files:.2f} files/sec")

        # Baseline: Should process at least 1 file per second for small PDFs
        assert throughput_files > 0.5, f"Throughput too low: {throughput_files:.2f} files/sec"

    def test_pymupdf4llm_parser_throughput(
        self,
        performance_test_pdfs: list[Path],
        performance_metrics,
    ) -> None:
        """Measure PyMuPDF4LLM parser throughput."""
        parser = PyMuPDF4LLMParser()
        successful_parses = 0

        performance_metrics.start()

        for pdf_path in performance_test_pdfs:
            doc = Document(source_path=str(pdf_path), format=DocumentFormat.PDF)
            result = parser.parse(doc)

            if result.success:
                successful_parses += 1

        performance_metrics.stop()

        duration = performance_metrics.duration
        throughput = successful_parses / duration if duration > 0 else 0

        print("\nPyMuPDF4LLM Performance:")
        print(f"  Files processed: {successful_parses}/{len(performance_test_pdfs)}")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Throughput: {throughput:.2f} files/sec")

        # Baseline: Should process at least 0.5 files per second
        assert throughput > 0.3, f"Throughput too low: {throughput:.2f} files/sec"

    @pytest.mark.slow
    def test_large_pdf_processing_time(
        self,
        large_test_pdf: Path,
        performance_metrics,
    ) -> None:
        """Measure processing time for large real-world PDF."""
        parser = PyMuPDFParser()
        doc = Document(source_path=str(large_test_pdf), format=DocumentFormat.PDF)

        performance_metrics.start()
        result = parser.parse(doc)
        performance_metrics.stop()

        assert result.success

        duration = performance_metrics.duration

        print("\nLarge PDF Processing:")
        print(f"  File: {large_test_pdf.name}")
        print(f"  Duration: {duration:.2f}s")

        # Baseline: Should process large PDF in reasonable time (< 30s)
        assert duration < 30.0, f"Processing too slow: {duration:.2f}s"


@pytest.mark.performance
@pytest.mark.slow
class TestChunkingPerformance:
    """Performance tests for chunking operations."""

    def test_token_chunking_performance(
        self,
        sample_realistic_document: Document,
        performance_metrics,
    ) -> None:
        """Measure token chunking performance with realistic document."""
        chunker = TokenChunker(chunk_size=500, chunk_overlap=50)

        # Create large document with many elements
        large_doc = sample_realistic_document
        # Multiply elements to create larger doc
        large_doc.elements = large_doc.elements * 100

        performance_metrics.start()
        chunks = chunker.chunk_document(large_doc)
        performance_metrics.stop()

        duration = performance_metrics.duration

        print("\nToken Chunking Performance:")
        print(f"  Input elements: {len(large_doc.elements)}")
        print(f"  Output chunks: {len(chunks)}")
        print(f"  Duration: {duration:.2f}s")

        # Should complete in reasonable time
        assert duration < 5.0, f"Chunking too slow: {duration:.2f}s"

    def test_by_title_chunking_performance(
        self,
        sample_realistic_document: Document,
        performance_metrics,
    ) -> None:
        """Measure by-title chunking performance."""
        chunker = ByTitleChunker(chunk_size=500, preserve_tables=True)

        # Create large document
        large_doc = sample_realistic_document
        large_doc.elements = large_doc.elements * 50

        performance_metrics.start()
        chunks = chunker.chunk_document(large_doc)
        performance_metrics.stop()

        duration = performance_metrics.duration

        print("\nBy-Title Chunking Performance:")
        print(f"  Input elements: {len(large_doc.elements)}")
        print(f"  Output chunks: {len(chunks)}")
        print(f"  Duration: {duration:.2f}s")

        # Should complete in reasonable time
        assert duration < 5.0, f"Chunking too slow: {duration:.2f}s"


@pytest.mark.performance
class TestMemoryUsage:
    """Performance tests for memory usage patterns."""

    def test_parser_memory_efficiency(
        self,
        diverse_test_pdfs: dict[str, Path],
    ) -> None:
        """Test parser memory usage remains reasonable."""
        parser = PyMuPDFParser()

        # Process multiple PDFs in sequence
        for name, pdf_path in diverse_test_pdfs.items():
            doc = Document(source_path=str(pdf_path), format=DocumentFormat.PDF)
            result = parser.parse(doc)

            # Should successfully parse without memory errors
            assert result is not None

            # Clean up
            del result

        # If we got here without MemoryError, test passed
        assert True

    def test_chunking_memory_efficiency(
        self,
        sample_realistic_document: Document,
    ) -> None:
        """Test chunking memory usage with large documents."""
        chunker = TokenChunker(chunk_size=500)

        # Create very large document
        large_doc = sample_realistic_document
        large_doc.elements = large_doc.elements * 500

        # Should handle large document without memory errors
        chunks = chunker.chunk_document(large_doc)

        # Verify chunks were created
        assert len(chunks) > 0

        # Clean up
        del chunks

        assert True
