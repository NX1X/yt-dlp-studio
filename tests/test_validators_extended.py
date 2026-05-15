"""Extended tests for src/utils/validators.py."""

from src.utils.validators import Validators


class TestIsValidDirectory:
    """Tests for Validators.is_valid_directory()."""

    def test_valid_directory(self, tmp_path):
        valid, error = Validators.is_valid_directory(str(tmp_path))
        assert valid is True
        assert error == ""

    def test_nonexistent_directory(self):
        valid, error = Validators.is_valid_directory("/nonexistent/path/12345")
        assert valid is False
        assert "does not exist" in error

    def test_file_not_directory(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        valid, error = Validators.is_valid_directory(str(f))
        assert valid is False
        assert "not a directory" in error

    def test_empty_path(self):
        valid, error = Validators.is_valid_directory("")
        assert valid is False
        assert "empty" in error.lower()

    def test_whitespace_only(self):
        valid, error = Validators.is_valid_directory("   ")
        assert valid is False


class TestValidateQualityChoice:
    """Tests for Validators.validate_quality_choice()."""

    def test_valid_quality(self):
        valid, error = Validators.validate_quality_choice("Best Quality")
        assert valid is True
        assert error == ""

    def test_invalid_quality(self):
        valid, error = Validators.validate_quality_choice("Fake Quality 999p")
        assert valid is False
        assert "Invalid" in error


class TestSanitizeFilenameExtended:
    """Extended tests for Validators.sanitize_filename()."""

    def test_all_invalid_chars(self):
        result = Validators.sanitize_filename('<>:"/\\|?*')
        assert result == "download"

    def test_multiple_spaces(self):
        result = Validators.sanitize_filename("hello   world   test")
        assert result == "hello world test"

    def test_leading_trailing_dots(self):
        result = Validators.sanitize_filename("...filename...")
        assert not result.startswith(".")
        assert not result.endswith(".")
