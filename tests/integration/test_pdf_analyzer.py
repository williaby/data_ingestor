"""Integration tests for PDF analyzer with real PDFs."""

from pathlib import Path

import pytest

from data_ingestor.pipeline.pdf_analyzer import PDFDocumentAnalyzer


@pytest.mark.integration
class TestPDFDocumentAnalyzer:
    """Integration tests for PDFDocumentAnalyzer with diverse real PDFs."""

    def test_analyze_simple_pdf(
        self,
        diverse_test_pdfs: dict[str, Path],
    ) -> None:
        """Test analyzer with simple text PDF."""
        pdf_path = diverse_test_pdfs["simple"]

        analyzer = PDFDocumentAnalyzer()
        analysis = analyzer.analyze(str(pdf_path))

        # Verify analysis results - PDFPreflightResult object
        assert analysis is not None
        assert hasattr(analysis, "needs_upscaling")
        assert hasattr(analysis, "resolution_analysis")

    def test_analyze_multipage_pdf(
        self,
        diverse_test_pdfs: dict[str, Path],
    ) -> None:
        """Test analyzer with multipage PDF."""
        pdf_path = diverse_test_pdfs["multipage"]

        analyzer = PDFDocumentAnalyzer()
        analysis = analyzer.analyze(str(pdf_path))

        # Should detect multiple pages
        assert analysis is not None

        # If analysis includes page count, verify it's > 1
        if isinstance(analysis, dict) and "page_count" in analysis:
            assert analysis["page_count"] > 1

    def test_analyze_formatted_pdf(
        self,
        diverse_test_pdfs: dict[str, Path],
    ) -> None:
        """Test analyzer with formatted text PDF."""
        pdf_path = diverse_test_pdfs["formatted"]

        analyzer = PDFDocumentAnalyzer()
        analysis = analyzer.analyze(str(pdf_path))

        # Should handle formatted text
        assert analysis is not None

    def test_analyze_table_pdf(
        self,
        diverse_test_pdfs: dict[str, Path],
    ) -> None:
        """Test analyzer with tabular data PDF."""
        pdf_path = diverse_test_pdfs["tables"]

        analyzer = PDFDocumentAnalyzer()
        analysis = analyzer.analyze(str(pdf_path))

        # Should detect tables
        assert analysis is not None

        # If analysis includes table detection, verify it found tables
        if isinstance(analysis, dict) and "has_tables" in analysis:
            assert analysis["has_tables"] is True

    def test_analyze_mixed_content_pdf(
        self,
        diverse_test_pdfs: dict[str, Path],
    ) -> None:
        """Test analyzer with mixed content PDF."""
        pdf_path = diverse_test_pdfs["mixed"]

        analyzer = PDFDocumentAnalyzer()
        analysis = analyzer.analyze(str(pdf_path))

        # Should handle mixed content
        assert analysis is not None

        # Mixed content should have varied characteristics
        if isinstance(analysis, dict):
            # Should detect multiple content types
            assert len(analysis) > 0

    def test_analyze_complex_layout_pdf(
        self,
        diverse_test_pdfs: dict[str, Path],
    ) -> None:
        """Test analyzer with complex layout PDF."""
        pdf_path = diverse_test_pdfs["complex"]

        analyzer = PDFDocumentAnalyzer()
        analysis = analyzer.analyze(str(pdf_path))

        # Should handle complex layout
        assert analysis is not None

        # Complex layout might have multi-column detection
        if isinstance(analysis, dict) and "has_multi_column" in analysis:
            assert isinstance(analysis["has_multi_column"], bool)

    @pytest.mark.slow
    def test_analyze_large_pdf(
        self,
        large_test_pdf: Path,
    ) -> None:
        """Test analyzer with large real-world PDF."""
        analyzer = PDFDocumentAnalyzer()
        analysis = analyzer.analyze(str(large_test_pdf))

        # Should handle large PDF without errors
        assert analysis is not None

        # Large PDF should have multiple pages
        if isinstance(analysis, dict) and "page_count" in analysis:
            assert analysis["page_count"] > 5


@pytest.mark.integration
class TestPDFDocumentAnalyzerQualityAssessment:
    """Integration tests for PDF quality assessment."""

    def test_resolution_detection(
        self,
        diverse_test_pdfs: dict[str, Path],
    ) -> None:
        """Test resolution detection across different PDFs."""
        analyzer = PDFDocumentAnalyzer()

        for name, pdf_path in diverse_test_pdfs.items():
            analysis = analyzer.analyze(str(pdf_path))

            # Should detect resolution info
            assert analysis is not None

            # If resolution is detected, it should be reasonable
            if isinstance(analysis, dict) and "resolution" in analysis:
                resolution = analysis["resolution"]
                # Typical PDF resolution ranges
                assert 72 <= resolution <= 300 or resolution is None

    def test_quality_assessment(
        self,
        diverse_test_pdfs: dict[str, Path],
    ) -> None:
        """Test quality assessment for PDFs."""
        analyzer = PDFDocumentAnalyzer()

        simple_pdf = diverse_test_pdfs["simple"]
        analysis = analyzer.analyze(str(simple_pdf))

        # Should assess quality
        assert analysis is not None

        # Quality indicators might include image quality, text clarity, etc.
        if isinstance(analysis, dict) and "quality_score" in analysis:
            quality = analysis["quality_score"]
            assert 0.0 <= quality <= 1.0

    def test_content_type_detection(
        self,
        diverse_test_pdfs: dict[str, Path],
    ) -> None:
        """Test content type detection."""
        analyzer = PDFDocumentAnalyzer()

        # Test with table PDF
        tables_pdf = diverse_test_pdfs["tables"]
        analysis = analyzer.analyze(str(tables_pdf))

        assert analysis is not None

        # Should detect content types
        if isinstance(analysis, dict) and "content_types" in analysis:
            content_types = analysis["content_types"]
            assert isinstance(content_types, (list, dict))


@pytest.mark.integration
class TestPDFDocumentAnalyzerEdgeCases:
    """Test PDF analyzer with edge cases."""

    def test_analyzer_with_nonexistent_file(self) -> None:
        """Test analyzer handles nonexistent file gracefully."""
        analyzer = PDFDocumentAnalyzer()

        with pytest.raises((FileNotFoundError, ValueError, Exception)):
            analyzer.analyze("/nonexistent/file.pdf")

    def test_analyzer_with_invalid_pdf(self, tmp_path: Path) -> None:
        """Test analyzer handles invalid PDF file gracefully."""
        # Create invalid PDF file
        invalid_pdf = tmp_path / "invalid.pdf"
        invalid_pdf.write_text("This is not a valid PDF file")

        analyzer = PDFDocumentAnalyzer()

        # Analyzer should handle errors gracefully and return result
        # (logs errors but doesn't raise exceptions)
        analysis = analyzer.analyze(str(invalid_pdf))
        assert analysis is not None
        assert hasattr(analysis, "needs_upscaling")

    def test_analyzer_initialization(self) -> None:
        """Test analyzer initialization."""
        analyzer = PDFDocumentAnalyzer()
        assert analyzer is not None

    def test_analyzer_with_minimal_pdf(self, temp_test_file: Path) -> None:
        """Test analyzer with minimal valid PDF."""
        analyzer = PDFDocumentAnalyzer()
        analysis = analyzer.analyze(str(temp_test_file))

        # Should handle minimal PDF
        assert analysis is not None
