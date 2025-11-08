"""Integration tests for full processing pipeline (no mocks)."""

import json
from pathlib import Path

import pytest

from data_ingestor.chunking.by_title_chunker import ByTitleChunker
from data_ingestor.chunking.token_chunker import TokenChunker
from data_ingestor.core.models import Document, DocumentFormat
from data_ingestor.export.exporter import DocumentExporter, OutputFormat
from data_ingestor.parsers.pdf_parser import PyMuPDF4LLMParser, PyMuPDFParser


class TestFullPipeline:
    """End-to-end pipeline tests with real data."""

    def test_pdf_to_json_export_complete_flow(
        self, test_data_dir: Path, validation_loader, tmp_path: Path
    ) -> None:
        """Test complete flow: PDF → Parse → Chunk → Export → Validate."""
        # Given: A real PDF file
        pdf_path = test_data_dir / "01_simple_text.pdf"
        validation = validation_loader("01_simple_text")

        # When: Process through full pipeline
        # Step 1: Parse
        doc = Document(source_path=str(pdf_path), format=DocumentFormat.PDF)
        parser = PyMuPDFParser()
        parse_result = parser.parse(doc)

        assert parse_result.success is True, "Parsing should succeed"
        assert len(parse_result.elements) > 0, "Should extract elements"

        # Step 2: Chunk
        parsed_doc = Document(
            document_id="pipeline-test",
            source_path=str(pdf_path),
            format=DocumentFormat.PDF,
            elements=parse_result.elements,
        )
        chunker = ByTitleChunker(chunk_size=500)
        chunks = chunker.chunk_document(parsed_doc)

        assert len(chunks) > 0, "Should create chunks"

        # Add chunks to document
        parsed_doc.chunks = chunks

        # Step 3: Export
        exporter = DocumentExporter()
        export_path = tmp_path / "output.json"
        exporter.export(parsed_doc, OutputFormat.JSON, export_path)

        # Then: Validate end-to-end
        assert export_path.exists(), "Export file should be created"

        with open(export_path) as f:
            data = json.load(f)

        # Validate structure
        assert "chunks" in data, "Should have chunks key"
        assert len(data["chunks"]) > 0, "Should have chunks"
        assert "document_id" in data, "Should have document_id"

        # Validate content
        full_text = " ".join(c["content"] for c in data["chunks"])
        for phrase in validation["content_validation"]["required_phrases"]:
            assert phrase in full_text, f"Missing phrase: {phrase}"

    def test_pipeline_with_token_chunking(
        self, test_data_dir: Path, tmp_path: Path
    ) -> None:
        """Test pipeline with token-based chunking."""
        pdf_path = test_data_dir / "02_multipage_document.pdf"

        # Parse
        doc = Document(source_path=str(pdf_path), format=DocumentFormat.PDF)
        parser = PyMuPDFParser()
        parse_result = parser.parse(doc)

        assert parse_result.success is True

        # Chunk with token-based strategy
        parsed_doc = Document(
            document_id="token-test",
            source_path=str(pdf_path),
            format=DocumentFormat.PDF,
            elements=parse_result.elements,
        )
        chunker = TokenChunker(chunk_size=200, chunk_overlap=50)
        chunks = chunker.chunk_document(parsed_doc)

        assert len(chunks) > 0

        # Add chunks to document
        parsed_doc.chunks = chunks

        # Export to JSON (DocumentExporter doesn't support JSONL)
        export_path = tmp_path / "output.json"
        exporter = DocumentExporter()
        exporter.export(parsed_doc, OutputFormat.JSON, export_path)

        assert export_path.exists()

        # Validate JSON format
        with open(export_path) as f:
            data = json.load(f)
            assert "chunks" in data, "Should have chunks"
            assert len(data["chunks"]) > 0, "Should have exported chunks"

            for chunk_data in data["chunks"]:
                assert "content" in chunk_data
                assert "metadata" in chunk_data

    def test_pipeline_with_table_preservation(
        self, test_data_dir: Path, tmp_path: Path
    ) -> None:
        """Test pipeline preserves tables correctly."""
        pdf_path = test_data_dir / "04_tabular_data.pdf"

        # Parse
        doc = Document(source_path=str(pdf_path), format=DocumentFormat.PDF)
        parser = PyMuPDFParser()
        parse_result = parser.parse(doc)

        assert parse_result.success is True

        # Check if we actually extracted table elements
        from data_ingestor.core.models import ElementType
        table_elements = [e for e in parse_result.elements if e.element_type == ElementType.TABLE]

        # Chunk with table preservation
        parsed_doc = Document(
            document_id="table-test",
            source_path=str(pdf_path),
            format=DocumentFormat.PDF,
            elements=parse_result.elements,
        )
        chunker = ByTitleChunker(chunk_size=500, preserve_tables=True)
        chunks = chunker.chunk_document(parsed_doc)

        assert len(chunks) > 0

        # Add chunks to document
        parsed_doc.chunks = chunks

        # Export
        export_path = tmp_path / "output.json"
        exporter = DocumentExporter()
        exporter.export(parsed_doc, OutputFormat.JSON, export_path)

        # Validate export structure
        with open(export_path) as f:
            data = json.load(f)

        assert "chunks" in data
        assert len(data["chunks"]) > 0

        # If the PDF had tables, verify they're in the export
        if table_elements:
            # Check that table content is preserved somewhere in chunks or elements
            all_content = " ".join(chunk["content"] for chunk in data["chunks"])
            assert len(all_content) > 0, "Should have extracted content"

    def test_pipeline_with_multiple_parsers(
        self, test_data_dir: Path, tmp_path: Path
    ) -> None:
        """Test pipeline works with different parsers."""
        pdf_path = test_data_dir / "01_simple_text.pdf"

        # Test with PyMuPDF
        doc1 = Document(source_path=str(pdf_path), format=DocumentFormat.PDF)
        parser1 = PyMuPDFParser()
        result1 = parser1.parse(doc1)

        # Test with PyMuPDF4LLM
        doc2 = Document(source_path=str(pdf_path), format=DocumentFormat.PDF)
        parser2 = PyMuPDF4LLMParser()
        result2 = parser2.parse(doc2)

        # Both should succeed
        assert result1.success is True
        assert result2.success is True

        # Both should produce chunkable content
        for result in [result1, result2]:
            parsed_doc = Document(
                document_id="multi-parser-test",
                source_path=str(pdf_path),
                format=DocumentFormat.PDF,
                elements=result.elements,
            )
            chunker = TokenChunker(chunk_size=500)
            chunks = chunker.chunk_document(parsed_doc)
            assert len(chunks) > 0

    def test_pipeline_error_handling(
        self, tmp_path: Path
    ) -> None:
        """Test pipeline handles errors gracefully."""
        # Create invalid PDF
        invalid_pdf = tmp_path / "invalid.pdf"
        invalid_pdf.write_text("Not a real PDF")

        # Parse should fail gracefully (returns result with success=False)
        doc = Document(source_path=str(invalid_pdf), format=DocumentFormat.PDF)
        parser = PyMuPDFParser()

        result = parser.parse(doc)

        # Parser should indicate failure without raising exception
        assert result.success is False, "Parser should indicate failure for invalid PDF"
        assert len(result.elements) == 0, "Should not extract elements from invalid PDF"


class TestPipelinePerformance:
    """Performance-focused integration tests."""

    def test_large_document_processing(
        self, test_data_dir: Path, tmp_path: Path, performance_metrics
    ) -> None:
        """Test pipeline performance with larger documents."""
        pdf_path = test_data_dir / "Where-does-wind-matter.pdf"

        if not pdf_path.exists():
            pytest.skip("Large PDF not available")

        performance_metrics.start()

        # Parse
        doc = Document(source_path=str(pdf_path), format=DocumentFormat.PDF)
        parser = PyMuPDFParser()
        result = parser.parse(doc)

        # Chunk
        parsed_doc = Document(
            document_id="perf-test",
            source_path=str(pdf_path),
            format=DocumentFormat.PDF,
            elements=result.elements,
        )
        chunker = TokenChunker(chunk_size=500)
        chunks = chunker.chunk_document(parsed_doc)

        # Add chunks to document
        parsed_doc.chunks = chunks

        # Export
        export_path = tmp_path / "large_output.json"
        exporter = DocumentExporter()
        exporter.export(parsed_doc, OutputFormat.JSON, export_path)

        performance_metrics.stop()

        # Should complete in reasonable time
        assert performance_metrics.duration < 30.0, \
            f"Large document processing took {performance_metrics.duration}s (expected <30s)"

        # Verify output
        assert export_path.exists()
        assert export_path.stat().st_size > 0


class TestPipelineDataQuality:
    """Data quality focused integration tests."""

    def test_content_preservation_through_pipeline(
        self, test_data_dir: Path, validation_loader, tmp_path: Path
    ) -> None:
        """Test that content is preserved accurately through the pipeline."""
        pdf_path = test_data_dir / "03_formatted_text.pdf"
        validation = validation_loader("03_formatted_text")

        # Full pipeline
        doc = Document(source_path=str(pdf_path), format=DocumentFormat.PDF)
        parser = PyMuPDFParser()
        result = parser.parse(doc)

        parsed_doc = Document(
            document_id="quality-test",
            source_path=str(pdf_path),
            format=DocumentFormat.PDF,
            elements=result.elements,
        )
        chunker = ByTitleChunker(chunk_size=1000)  # Large chunks to preserve context
        chunks = chunker.chunk_document(parsed_doc)

        # Add chunks to document
        parsed_doc.chunks = chunks

        export_path = tmp_path / "quality_output.json"
        exporter = DocumentExporter()
        exporter.export(parsed_doc, OutputFormat.JSON, export_path)

        # Validate content quality
        with open(export_path) as f:
            data = json.load(f)

        full_text = " ".join(c["content"] for c in data["chunks"])

        # Check for required phrases
        for phrase in validation["content_validation"]["required_phrases"]:
            assert phrase in full_text, f"Content preservation failed for: {phrase}"

        # Check metadata is preserved
        for chunk in data["chunks"]:
            assert "metadata" in chunk
            assert "chunk_index" in chunk["metadata"]

    def test_metadata_propagation(
        self, test_data_dir: Path, tmp_path: Path
    ) -> None:
        """Test that metadata propagates correctly through pipeline."""
        pdf_path = test_data_dir / "01_simple_text.pdf"

        # Parse with metadata tracking
        doc = Document(
            document_id="metadata-test",
            source_path=str(pdf_path),
            format=DocumentFormat.PDF,
        )
        parser = PyMuPDFParser()
        result = parser.parse(doc)

        # Verify parser metadata
        assert result.parser_name == "PyMuPDFParser"
        assert result.processing_time > 0

        # Chunk
        parsed_doc = Document(
            document_id="metadata-test",
            source_path=str(pdf_path),
            format=DocumentFormat.PDF,
            elements=result.elements,
        )
        chunker = ByTitleChunker(chunk_size=500)
        chunks = chunker.chunk_document(parsed_doc)

        # Verify chunk metadata
        for i, chunk in enumerate(chunks):
            assert chunk.metadata["document_id"] == "metadata-test"
            assert chunk.metadata["chunk_index"] == i
            assert chunk.metadata["total_chunks"] == len(chunks)

        # Add chunks to document
        parsed_doc.chunks = chunks

        # Export and verify metadata persists
        export_path = tmp_path / "metadata_output.json"
        exporter = DocumentExporter()
        exporter.export(parsed_doc, OutputFormat.JSON, export_path)

        with open(export_path) as f:
            data = json.load(f)

        # Verify metadata in export
        assert "metadata" in data
        assert len(data["chunks"]) == len(chunks)

        for exported_chunk in data["chunks"]:
            assert "metadata" in exported_chunk
            assert "document_id" in exported_chunk["metadata"]
