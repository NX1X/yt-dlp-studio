"""
Sync version_info.txt from the canonical __version__ in src/__init__.py.

Run this after bumping __version__:

    python scripts/sync_version.py

It rewrites version_info.txt (the Windows EXE metadata resource read by
PyInstaller via build.spec) so the embedded ProductVersion and FileVersion
match the Python package version. It does not touch CHANGELOG.md, ROADMAP.md,
or any narrative docs — those need human-written release notes.

Exits 0 on success, 1 if __version__ can't be parsed, 2 if version_info.txt
is missing.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INIT_FILE = REPO_ROOT / "src" / "__init__.py"
VERSION_INFO = REPO_ROOT / "packaging" / "version_info.txt"

_SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$")


def read_canonical_version() -> str:
    text = INIT_FILE.read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        print(f"ERROR: could not find __version__ in {INIT_FILE}", file=sys.stderr)
        sys.exit(1)
    return match.group(1)


def to_tuple(version: str) -> tuple[int, int, int, int]:
    """Convert '0.9.2' or '0.9.2-beta.1' to a (major, minor, patch, 0) tuple
    suitable for the Windows VS_FIXEDFILEINFO 4-part version field."""
    m = _SEMVER.match(version)
    if not m:
        print(f"ERROR: '{version}' is not a valid semver string", file=sys.stderr)
        sys.exit(1)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)), 0)


def update_version_info(version: str) -> bool:
    if not VERSION_INFO.exists():
        print(f"ERROR: {VERSION_INFO} not found", file=sys.stderr)
        sys.exit(2)

    tup = to_tuple(version)
    text = VERSION_INFO.read_text(encoding="utf-8")
    original = text

    text = re.sub(
        r"filevers=\(\d+,\s*\d+,\s*\d+,\s*\d+\)",
        f"filevers=({tup[0]}, {tup[1]}, {tup[2]}, {tup[3]})",
        text,
    )
    text = re.sub(
        r"prodvers=\(\d+,\s*\d+,\s*\d+,\s*\d+\)",
        f"prodvers=({tup[0]}, {tup[1]}, {tup[2]}, {tup[3]})",
        text,
    )
    text = re.sub(
        r"StringStruct\(u'FileVersion', u'[^']*'\)",
        f"StringStruct(u'FileVersion', u'{tup[0]}.{tup[1]}.{tup[2]}.{tup[3]}')",
        text,
    )
    text = re.sub(
        r"StringStruct\(u'ProductVersion', u'[^']*'\)",
        f"StringStruct(u'ProductVersion', u'{version}')",
        text,
    )

    if text == original:
        print(f"version_info.txt already in sync at v{version}")
        return False

    VERSION_INFO.write_text(text, encoding="utf-8")
    print(f"Updated version_info.txt -> v{version} ({'.'.join(map(str, tup))})")
    return True


def main() -> None:
    version = read_canonical_version()
    print(f"Canonical version (src/__init__.py): {version}")
    update_version_info(version)


if __name__ == "__main__":
    main()
