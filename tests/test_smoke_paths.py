"""The test run must never use the real app data folder (see tests/conftest.py)."""

import os
import tempfile

from src.utils.constants import APP_DATA_DIR, LOG_PATH


def test_app_data_dir_is_in_the_temp_folder():
    temp = os.path.realpath(tempfile.gettempdir())
    assert os.path.realpath(APP_DATA_DIR).startswith(temp)
    assert os.path.realpath(LOG_PATH).startswith(temp)
