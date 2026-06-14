"""
Sync derived version files from the canonical __version__ in src/__init__.py.

Run this after bumping __version__:

    python scripts/sync_version.py

It updates every file that mirrors the source-of-truth version:

* ``packaging/version_info.txt`` - the Windows EXE metadata resource that
  PyInstaller embeds via ``build.spec``. Both ``filevers`` / ``prodvers``
  tuples and the FileVersion / ProductVersion strings are rewritten.

* ``CHANGELOG.md`` - the ``## [Unreleased]`` section header is stamped to
  ``## [<version>] - <YYYY-MM-DD>`` and a fresh empty ``## [Unreleased]``
  block is prepended so the next development cycle has a place to write.
  Skipped when there is no ``## [Unreleased]`` section, when a section for
  this version already exists, or when the ``## [Unreleased]`` body is empty
  (in which case the script prints a warning rather than committing an
  empty release).

This way bumping a release version is one edit (``__version__`` in
``src/__init__.py``) plus one command (``python scripts/sync_version.py``)
with no manual stamping of mirrored files.

Exit codes:
    0  success
    1  ``__version__`` could not be parsed
    2  ``version_info.txt`` is missing
    3  CHANGELOG.md is present but the ``## [Unreleased]`` body is empty
"""

from __future__ import annotations

import re
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INIT_FILE = REPO_ROOT / "src" / "__init__.py"
VERSION_INFO = REPO_ROOT / "packaging" / "version_info.txt"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"

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


def cut_changelog(version: str) -> int:
    """Stamp the ``## [Unreleased]`` block in CHANGELOG.md as the given version.

    Returns one of:
        0  - section stamped (or already up-to-date for ``version``).
        1  - non-fatal skip (no Unreleased section, or CHANGELOG missing).
        3  - the Unreleased body is empty; refused to commit an empty release.
    """
    if not CHANGELOG.exists():
        print(f"NOTE: {CHANGELOG} not found; skipping CHANGELOG stamp")
        return 1

    text = CHANGELOG.read_text(encoding="utf-8")

    # Idempotency: if the version section already exists, do not stamp again.
    if re.search(rf"^## \[{re.escape(version)}\] -", text, re.MULTILINE):
        print(f"CHANGELOG.md already has a section for {version}; nothing to do")
        return 0

    # Locate the Unreleased section. We expect the header line ``## [Unreleased]``
    # followed by the section body, ending at the next ``## [...]`` header or
    # the end of file. The body is everything between the header and the next
    # version section's header line.
    header_pattern = re.compile(r"^## \[Unreleased\]\s*$", re.MULTILINE)
    header_match = header_pattern.search(text)
    if not header_match:
        print("NOTE: no ## [Unreleased] section in CHANGELOG.md; skipping stamp")
        return 1

    body_start = header_match.end()
    # Search for the next versioned header (start of next section).
    next_header = re.search(r"^## \[[^\]]+\] - ", text[body_start:], re.MULTILINE)
    body_end = body_start + next_header.start() if next_header else len(text)

    body = text[body_start:body_end].strip()
    # Strip any optional ``---`` divider that often precedes the next section.
    body_no_divider = re.sub(r"\s*^---\s*$", "", body, count=1, flags=re.MULTILINE).strip()

    if not body_no_divider:
        print("ERROR: ## [Unreleased] section has no content; refusing to cut an empty release", file=sys.stderr)
        return 3

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    new_header = f"## [Unreleased]\n\n_(no entries yet)_\n\n---\n\n## [{version}] - {today}\n"
    new_text = text[: header_match.start()] + new_header + text[header_match.end() :]

    CHANGELOG.write_text(new_text, encoding="utf-8")
    print(f"Stamped CHANGELOG.md: [Unreleased] -> [{version}] - {today}")
    return 0


def main() -> None:
    version = read_canonical_version()
    print(f"Canonical version (src/__init__.py): {version}")
    update_version_info(version)
    rc = cut_changelog(version)
    if rc == 3:
        sys.exit(3)


if __name__ == "__main__":
    main()
