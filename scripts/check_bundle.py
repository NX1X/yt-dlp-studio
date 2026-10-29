"""Check that a built single-file executable contains what it needs to work.

Run in CI right after PyInstaller, on the same runner:

    python scripts/check_bundle.py dist/yt-dlp-studio.exe   # Windows
    python scripts/check_bundle.py dist/yt-dlp-studio       # Linux

Why: v0.1.3 shipped an EXE without the yt-dlp-ejs solver scripts. The build
passed, the tests passed (they run from source), and YouTube downloads failed
for every user. This script opens the bundle itself and fails the build when
a critical file is missing or a banned package got in.

Exit code 0 means every check passed; 1 means at least one failed.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from PyInstaller.archive.readers import CArchiveReader

ROOT = Path(__file__).resolve().parent.parent

# Needed on every platform.
REQUIRED_COMMON = [
    # yt-dlp-ejs solver scripts: DATA files, so hiddenimports alone misses them.
    "yt_dlp_ejs/yt/solver/core.min.js",
    "yt_dlp_ejs/yt/solver/lib.min.js",
    # The vendored engine.
    "yt_dlp_engine/yt_dlp/version.py",
    "yt_dlp_engine/yt_dlp/YoutubeDL.py",
]

# Windows bundles FFmpeg and Deno; Linux uses the system FFmpeg and installs
# Deno on first run (see packaging/build_linux.spec).
REQUIRED_WINDOWS = [
    "ffmpeg.exe",
    "ffprobe.exe",
    "deno.exe",
    "avcodec-62.dll",
    "avdevice-62.dll",
    "avfilter-11.dll",
    "avformat-62.dll",
    "avutil-60.dll",
    "swresample-6.dll",
    "swscale-9.dll",
]

# Pure-Python modules that must be in the embedded PYZ archive.
REQUIRED_MODULES = [
    "yt_dlp_ejs",
    "src.backend.yt_dlp_wrapper",
]

# Compiled extensions are stored as files, not PYZ modules: `.pyd` on Windows,
# `.abi3.so` (or another `.so` suffix) on Linux. Matched as patterns.
REQUIRED_EXTENSIONS = [
    re.compile(r"^PySide6/QtCore\.(pyd|.*so)$"),
    re.compile(r"^PySide6/QtWidgets\.(pyd|.*so)$"),
]

# Banned by the project's software-origin policy. Matched against every
# file name in the bundle and every module name in the PYZ.
FORBIDDEN = re.compile(r"curl_cffi|libcurl-impersonate", re.IGNORECASE)


def _normalise(name: str) -> str:
    return name.replace("\\", "/")


def check(exe: Path) -> list[str]:
    """Return a list of failure messages (empty means the bundle is good)."""
    failures: list[str] = []
    archive = CArchiveReader(str(exe))
    files = {_normalise(n) for n in archive.toc}

    required = list(REQUIRED_COMMON)
    if exe.suffix.lower() == ".exe":
        required += REQUIRED_WINDOWS
    for name in required:
        if name not in files:
            failures.append(f"missing file: {name}")

    pyz_names = [n for n in archive.toc if _normalise(n).endswith(".pyz")]
    modules: set[str] = set()
    for pyz in pyz_names:
        modules |= set(archive.open_embedded_archive(pyz).toc)
    if not modules:
        failures.append("no embedded PYZ archive found")
    for mod in REQUIRED_MODULES:
        if mod not in modules:
            failures.append(f"missing module: {mod}")
    for pattern in REQUIRED_EXTENSIONS:
        if not any(pattern.match(n) for n in files):
            failures.append(f"missing extension: {pattern.pattern}")

    for name in sorted(files | modules):
        if FORBIDDEN.search(name):
            failures.append(f"forbidden content: {name}")

    # The bundled engine must be the version the app reports.
    version_src = archive.extract("yt_dlp_engine/yt_dlp/version.py") if "yt_dlp_engine/yt_dlp/version.py" in files else b""
    bundled = re.search(rb"__version__\s*=\s*'([^']+)'", version_src or b"")
    constants = (ROOT / "src" / "utils" / "constants.py").read_text(encoding="utf-8")
    expected = re.search(r'YTDLP_VERSION\s*=\s*"([^"]+)"', constants)
    if bundled and expected and bundled.group(1).decode() != expected.group(1):
        failures.append(f"bundled yt-dlp {bundled.group(1).decode()} != YTDLP_VERSION {expected.group(1)}")

    print(f"{exe}: {len(files)} files, {len(modules)} modules checked")
    return failures


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    exe = Path(sys.argv[1])
    if not exe.is_file():
        print(f"FAIL: {exe} does not exist")
        return 1
    failures = check(exe)
    for f in failures:
        print(f"FAIL: {f}")
    if failures:
        return 1
    print("OK: bundle contains every required file and module, and nothing forbidden")
    return 0


if __name__ == "__main__":
    sys.exit(main())
