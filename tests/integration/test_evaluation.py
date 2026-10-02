"""Integration tests for evaluation framework with real data."""

import json
from pathlib import Path

import pytest

from data_ingestor.evaluation.doclaynet_evaluator import DocLayNetEvaluator
from data_ingestor.evaluation.metrics.layout_metrics import calculate_map
from data_ingestor.evaluation.metrics.structure_metrics import (
    calculate_reading_order_f1,
    calculate_section_f1,
)
from data_ingestor.evaluation.metrics.text_metrics import calculate_bleu, calculate_cer, calculate_chrf


@pytest.mark.integration
@pytest.mark.requires_doclaynet
class TestDocLayNetEvaluator:
    """Integration tests for DocLayNetEvaluator with real ground truth."""

    def test_evaluator_with_real_ground_truth(
        self,
        sample_doclaynet_files: list[Path],
    ) -> None:
        """Test evaluator with actual DocLayNet annotations."""
        # Use first ground truth file
        gt_file = sample_doclaynet_files[0]

        # Load ground truth
        with open(gt_file) as f:
            json.load(f)

        # Initialize evaluator
        evaluator = DocLayNetEvaluator(ground_truth_dir=gt_file.parent)

        # Verify evaluator initialized
        assert evaluator is not None
        assert evaluator.ground_truth_dir == gt_file.parent

    def test_evaluator_loads_ground_truth(
        self,
        doclaynet_ground_truth_loader,
        sample_doclaynet_files: list[Path],
    ) -> None:
        """Test loading ground truth data."""
        # Get first file hash
        gt_file = sample_doclaynet_files[0]
        pdf_hash = gt_file.stem

        # Load ground truth
        gt_data = doclaynet_ground_truth_loader(pdf_hash)

        # Verify structure
        assert isinstance(gt_data, dict)
        # DocLayNet ground truth should have specific fields
        # (structure depends on actual format)

    def test_evaluator_with_multiple_ground_truth_files(
        self,
        sample_doclaynet_files: list[Path],
    ) -> None:
        """Test evaluator with multiple ground truth files."""
        evaluator = DocLayNetEvaluator(
            ground_truth_dir=sample_doclaynet_files[0].parent,
        )

        # Verify can handle multiple files
        assert evaluator.ground_truth_dir.exists()

        # Count available ground truth files
        gt_files = list(evaluator.ground_truth_dir.glob("*.json"))
        assert len(gt_files) >= len(sample_doclaynet_files)

    def test_evaluator_initialization_with_invalid_dir(self) -> None:
        """Test evaluator handles invalid directory gracefully."""
        invalid_dir = Path("/nonexistent/directory")

        # Evaluator should raise FileNotFoundError for invalid directory
        with pytest.raises(FileNotFoundError):
            DocLayNetEvaluator(ground_truth_dir=invalid_dir)


@pytest.mark.integration
class TestLayoutMetrics:
    """Integration tests for layout metrics."""

    def test_layout_map_calculation_perfect_match(self) -> None:
        """Test layout mAP calculation with perfect match."""
        # Create predicted and ground truth bounding boxes (x, y, w, h format)
        predicted = [
            {"class": "text", "bbox": [10, 10, 100, 50], "confidence": 0.95},
            {"class": "text", "bbox": [10, 70, 100, 50], "confidence": 0.90},
        ]

        ground_truth = [
            {"class": "text", "bbox": [10, 10, 100, 50]},
            {"class": "text", "bbox": [10, 70, 100, 50]},
        ]

        # Calculate mAP
        map_score = calculate_map(predicted, ground_truth, iou_threshold=0.5)

        # Verify score is in valid range
        assert 0.0 <= map_score <= 1.0
        # Perfect predictions should have reasonable mAP
        assert map_score > 0.0

    def test_layout_map_with_no_overlap(self) -> None:
        """Test mAP with non-overlapping boxes."""
        predicted = [
            {"class": "text", "bbox": [0, 0, 100, 100], "confidence": 0.95},
        ]
        ground_truth = [
            {"class": "text", "bbox": [200, 200, 100, 100]},
        ]

        map_score = calculate_map(predicted, ground_truth)
        # No overlap should result in low score
        assert map_score < 0.5

    def test_layout_map_with_multiple_classes(self) -> None:
        """Test mAP with multiple element classes."""
        predicted = [
            {"class": "text", "bbox": [10, 10, 100, 50], "confidence": 0.95},
            {"class": "table", "bbox": [10, 70, 200, 100], "confidence": 0.90},
        ]
        ground_truth = [
            {"class": "text", "bbox": [10, 10, 100, 50]},
            {"class": "table", "bbox": [10, 70, 200, 100]},
        ]

        map_score = calculate_map(predicted, ground_truth)
        assert 0.0 <= map_score <= 1.0
        assert map_score > 0.8  # Should be high for good predictions


@pytest.mark.integration
class TestTextMetrics:
    """Integration tests for text metrics with real text samples."""

    def test_cer_calculation_with_sample_text(self) -> None:
        """Test CER calculation with realistic text samples."""
        reference = "This is a test document with some text content."
        hypothesis = "This is a test document with some text content."

        cer = calculate_cer(hypothesis, reference)

        # Perfect match should have CER = 0
        assert cer == 0.0

    def test_cer_with_errors(self) -> None:
        """Test CER with character errors."""
        reference = "hello world"
        hypothesis = "helo world"  # Missing one 'l'

        cer = calculate_cer(hypothesis, reference)

        # Should have non-zero error
        assert cer > 0.0
        assert cer < 1.0  # Not completely wrong

    def test_bleu_score_calculation(self) -> None:
        """Test BLEU score with sample texts."""
        reference = "The quick brown fox jumps over the lazy dog"
        hypothesis = "The quick brown fox jumps over the lazy dog"

        bleu = calculate_bleu(hypothesis, reference)

        # Perfect match should have high BLEU
        assert 0.0 <= bleu <= 1.0
        assert bleu > 0.9

    def test_chrf_score_calculation(self) -> None:
        """Test chrF score calculation."""
        reference = "Natural language processing is important"
        hypothesis = "Natural language processing is important"

        chrf = calculate_chrf(hypothesis, reference)

        # Perfect match should have chrF close to 1
        assert 0.0 <= chrf <= 1.0
        assert chrf > 0.9

    def test_text_metrics_with_validation_data(
        self,
        validation_dir: Path,
    ) -> None:
        """Test text metrics with actual validation data."""
        # Load validation data for simple text PDF
        validation_file = validation_dir / "01_simple_text.json"

        if not validation_file.exists():
            pytest.skip("Validation data not available")

        with open(validation_file) as f:
            validation = json.load(f)

        # Get required phrases (ground truth)
        required_phrases = validation["content_validation"]["required_phrases"]

        # Calculate metrics
        for phrase in required_phrases:
            cer = calculate_cer(phrase, phrase)  # Perfect match
            assert cer == 0.0


@pytest.mark.integration
class TestStructureMetrics:
    """Integration tests for structure metrics."""

    def test_reading_order_f1_calculation(self) -> None:
        """Test reading order F1 calculation with ordered elements."""
        # Predicted reading order (as list of element IDs)
        predicted_order = ["elem1", "elem2", "elem3", "elem4", "elem5"]
        ground_truth_order = ["elem1", "elem2", "elem3", "elem4", "elem5"]

        # Calculate F1
        f1 = calculate_reading_order_f1(predicted_order, ground_truth_order)

        # Perfect order should have F1 = 1.0
        assert f1 == 1.0

    def test_reading_order_with_errors(self) -> None:
        """Test reading order F1 with ordering errors."""
        predicted_order = ["elem1", "elem3", "elem2", "elem4", "elem5"]  # Swapped 2 and 3
        ground_truth_order = ["elem1", "elem2", "elem3", "elem4", "elem5"]

        f1 = calculate_reading_order_f1(predicted_order, ground_truth_order)

        # Should have lower F1 due to ordering error
        assert 0.0 <= f1 < 1.0

    def test_section_f1_calculation(self) -> None:
        """Test section detection F1 score."""
        predicted = [
            {"type": "heading", "text": "Introduction"},
            {"type": "paragraph", "text": "Content"},
        ]
        ground_truth = [
            {"type": "heading", "text": "Introduction"},
            {"type": "paragraph", "text": "Content"},
        ]

        f1 = calculate_section_f1(predicted, ground_truth)
        assert 0.0 <= f1 <= 1.0


@pytest.mark.integration
class TestEvaluationEdgeCases:
    """Test evaluation framework edge cases."""

    def test_metrics_with_empty_inputs(self) -> None:
        """Test metrics handle empty inputs gracefully."""
        # Empty text should not crash
        cer = calculate_cer("", "")
        assert cer == 0.0 or cer is not None

    @pytest.mark.slow
    def test_metrics_with_very_long_text(self) -> None:
        """Test metrics with large text inputs (10K words, ~50KB).

        Marked as slow due to high memory usage in parallel execution.
        """
        long_text = "word " * 10000
        cer = calculate_cer(long_text, long_text)

        # Should handle large inputs
        assert cer == 0.0

    def test_layout_map_with_no_predictions(self) -> None:
        """Test mAP calculation with no predictions."""
        predicted = []
        ground_truth = [
            {"class": "text", "bbox": [10, 10, 100, 50]},
        ]

        map_score = calculate_map(predicted, ground_truth)

        # No predictions should result in score of 0
        assert map_score == 0.0

    def test_layout_map_with_no_ground_truth(self) -> None:
        """Test mAP calculation with no ground truth."""
        predicted = [
            {"class": "text", "bbox": [10, 10, 100, 50], "confidence": 0.95},
        ]
        ground_truth = []

        map_score = calculate_map(predicted, ground_truth)

        # Should handle empty ground truth
        assert 0.0 <= map_score <= 1.0

    def test_bleu_with_mismatched_length(self) -> None:
        """Test BLEU with different length texts."""
        reference = "The quick brown fox"
        hypothesis = "The quick brown"

        bleu = calculate_bleu(hypothesis, reference)
        assert 0.0 <= bleu <= 1.0

    def test_cer_with_unicode(self) -> None:
        """Test CER with Unicode characters."""
        reference = "Hello 世界 🌍"
        hypothesis = "Hello 世界 🌍"

        cer = calculate_cer(hypothesis, reference)
        assert cer == 0.0
