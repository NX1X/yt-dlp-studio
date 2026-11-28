"""Root conftest.py for YT-DLP Studio test suite."""

import os
import sys
from pathlib import Path

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Headless Qt for CI
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
