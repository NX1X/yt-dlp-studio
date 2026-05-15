# Tests for YT-DLP Studio

Test suite for the application.

## Running Tests

### Run all tests:
```bash
pytest tests/ -v
```

### Run specific test file:
```bash
pytest tests/test_config_manager.py -v
```

### Run specific test:
```bash
pytest tests/test_validators.py::TestURLValidation::test_valid_youtube_url -v
```

### With coverage:
```bash
pytest tests/ --cov=src --cov-report=html
```

## Test Structure

```
tests/
├── __init__.py
├── test_config_manager.py      # Config persistence tests
├── test_validators.py           # Input validation tests
├── test_file_helper.py         # TODO: File utilities tests
├── test_format_handler.py      # TODO: Format selection tests
├── test_download_task.py       # TODO: Data model tests
└── README.md                   # This file
```

## Writing Tests

### Test Naming Convention

- **Files:** `test_<module_name>.py`
- **Classes:** `Test<FeatureName>`
- **Methods:** `test_<what_it_tests>`

### Example Test

```python
import pytest
from src.backend.some_module import SomeClass

class TestSomeFeature:
    """Test suite for SomeFeature."""

    @pytest.fixture
    def setup_data(self):
        """Setup test data."""
        return {"key": "value"}

    def test_something(self, setup_data):
        """Test that something works."""
        result = SomeClass.do_something(setup_data)
        assert result is not None
```

## Current Test Coverage

**Status:** Minimal (v1.0 focus is manual testing)

**Existing Tests:**
- ✅ ConfigManager basic functionality
- ✅ URL validation
- ✅ Filename sanitization

**TODO:**
- ⏳ File helper utilities
- ⏳ Format handler
- ⏳ Download task model
- ⏳ Progress handler
- ⏳ yt-dlp wrapper (integration tests)
- ⏳ UI components (requires pytest-qt)

## Integration Tests

**Note:** Integration tests that require network access or yt-dlp downloads should be marked with `@pytest.mark.integration` and skipped by default.

Example:
```python
@pytest.mark.integration
def test_real_download():
    """Test actual download (requires network)."""
    # Test code
```

Run only integration tests:
```bash
pytest tests/ -m integration
```

Skip integration tests:
```bash
pytest tests/ -m "not integration"
```

## Testing Guidelines

1. **Unit tests:** Test individual functions/methods in isolation
2. **Keep tests fast:** Mock external dependencies
3. **One assertion per test:** Test one thing at a time
4. **Use fixtures:** For common setup/teardown
5. **Test edge cases:** Empty strings, None values, etc.

## Future Improvements

- Increase code coverage to >80%
- Add integration tests for download workflow
- Add UI tests using pytest-qt
- Set up continuous integration (GitHub Actions)
- Add performance tests
- Add regression tests

---

**Last Updated:** 2024-10-26
