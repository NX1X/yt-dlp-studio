"""
Keep the test run away from the real app data folder.

The app picks its data folder (settings, history, queue, the log and crash
reports) when ``src.utils.constants`` is imported, from the home folder or
%APPDATA%. Without this file every test run wrote to the developer's real
``~/.config/YT-DLP Studio`` log. pytest loads this file before any test
module, so pointing HOME and APPDATA at a temporary folder here is early
enough. Tests that need their own folder still patch paths as before.
"""

import atexit
import os
import shutil
import tempfile

_TEST_HOME = tempfile.mkdtemp(prefix="yt-dlp-studio-tests-")
os.environ["HOME"] = _TEST_HOME
os.environ["USERPROFILE"] = _TEST_HOME
os.environ["APPDATA"] = os.path.join(_TEST_HOME, "AppData", "Roaming")
os.environ["XDG_CONFIG_HOME"] = os.path.join(_TEST_HOME, ".config")
atexit.register(shutil.rmtree, _TEST_HOME, ignore_errors=True)
