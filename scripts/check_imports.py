"""
Sanity-check that every module needed at PyInstaller build time can be imported.

Run BEFORE building the .exe to catch missing modules early instead of after a
20-minute build:

    python scripts/check_imports.py

Exits 0 when all checks pass, 1 otherwise.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENGINE_PATH = REPO_ROOT / "vendor" / "yt_dlp_engine"


def _check_import(module_name: str, description: str = "") -> bool:
    try:
        __import__(module_name)
        print(f"[OK]    {module_name:40} {description}")
        return True
    except ImportError as e:
        print(f"[FAIL]  {module_name:40} {e}")
        return False
    except Exception as e:
        print(f"[ERROR] {module_name:40} {e}")
        return False


def main() -> int:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 80)
    print("Checking imports for YT-DLP Studio")
    print("=" * 80)

    all_passed = True

    print("\n[Python Standard Library Modules]")
    print("-" * 80)
    stdlib_modules = [
        ("optparse", "Used by yt-dlp"),
        ("xml.etree", "XML parsing"),
        ("xml.etree.ElementTree", "XML tree parsing"),
        ("collections", "Container datatypes"),
        ("getpass", "Password input"),
        ("itertools", "Iterator functions"),
        ("os", "Operating system interface"),
        ("re", "Regular expressions"),
        ("traceback", "Stack trace"),
        ("subprocess", "Process management"),
        ("json", "JSON parsing"),
        ("urllib", "URL handling"),
        ("http", "HTTP libraries"),
        ("email", "Email handling"),
    ]
    for module, desc in stdlib_modules:
        if not _check_import(module, desc):
            all_passed = False

    print("\n[GUI Framework — PySide6]")
    print("-" * 80)
    for module, desc in [
        ("PySide6", "Qt for Python"),
        ("PySide6.QtCore", "Qt Core"),
        ("PySide6.QtGui", "Qt GUI"),
        ("PySide6.QtWidgets", "Qt Widgets"),
    ]:
        if not _check_import(module, desc):
            all_passed = False

    print("\n[Third-Party Dependencies]")
    print("-" * 80)
    for module, desc in [
        ("requests", "HTTP library"),
        ("packaging", "Version comparison"),
    ]:
        if not _check_import(module, desc):
            all_passed = False

    print("\n[yt-dlp Engine (vendored)]")
    print("-" * 80)
    if str(ENGINE_PATH) not in sys.path:
        sys.path.insert(0, str(ENGINE_PATH))
    try:
        from yt_dlp import version  # noqa: F401

        print(f"[OK]    yt_dlp                                   Version: {version.__version__}")
    except Exception as e:
        print(f"[FAIL]  yt_dlp                                   {e}")
        all_passed = False
        traceback.print_exc()

    print("\n" + "=" * 80)
    if all_passed:
        print("[SUCCESS] All checks passed — safe to build")
        return 0
    print("[FAILED] Some checks failed — fix before building")
    return 1


if __name__ == "__main__":
    sys.exit(main())
