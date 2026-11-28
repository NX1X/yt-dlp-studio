"""Root conftest.py for YT-DLP Studio test suite."""

import os
import sys
from pathlib import Path

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Headless Qt for CI
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_download_preferences():
    """Start every test with the default advanced download settings.

    ConfigManager publishes the settings to a module-level value; a test
    that saves a proxy or cookies must not leak them into the next test.
    """
    from src.backend import download_preferences

    download_preferences.set_download_preferences(download_preferences.DownloadPreferences())
    yield
    download_preferences.set_download_preferences(download_preferences.DownloadPreferences())
