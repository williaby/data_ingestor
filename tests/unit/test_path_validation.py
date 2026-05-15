"""Unit tests for path validation helper."""

from pathlib import Path

import pytest

from data_ingestor.utils.path_validation import UnsafePathError, validate_output_path


class TestValidateOutputPath:
    def test_relative_path_inside_base(self, tmp_path: Path) -> None:
        result = validate_output_path("report.json", tmp_path)
        assert result == (tmp_path / "report.json").resolve()

    def test_nested_relative_path_inside_base(self, tmp_path: Path) -> None:
        result = validate_output_path("sub/report.json", tmp_path)
        assert result == (tmp_path / "sub" / "report.json").resolve()

    def test_absolute_path_inside_base(self, tmp_path: Path) -> None:
        target = tmp_path / "x.json"
        result = validate_output_path(target, tmp_path)
        assert result == target.resolve()

    def test_rejects_dotdot_traversal(self, tmp_path: Path) -> None:
        with pytest.raises(UnsafePathError):
            validate_output_path("../escape.json", tmp_path)

    def test_rejects_deep_dotdot_traversal(self, tmp_path: Path) -> None:
        with pytest.raises(UnsafePathError):
            validate_output_path("a/b/../../../escape.json", tmp_path)

    def test_rejects_absolute_outside_base(self, tmp_path: Path) -> None:
        with pytest.raises(UnsafePathError):
            validate_output_path("/etc/passwd", tmp_path)

    def test_rejects_symlink_escape(self, tmp_path: Path) -> None:
        outside = tmp_path.parent / "outside_dir"
        outside.mkdir(exist_ok=True)
        link = tmp_path / "escape"
        link.symlink_to(outside, target_is_directory=True)
        with pytest.raises(UnsafePathError):
            validate_output_path("escape/sneaky.json", tmp_path)
