"""
Deno auto-installer for YT-DLP Studio.

Downloads the Deno JS runtime on first run if it is not present.
yt-dlp needs Deno to solve YouTube's JS challenges and unlock all
available formats. Pinned to v2.9.8 to match the CI build.

Where Deno comes from:

- Frozen Windows build: deno.exe is bundled in the EXE. No download.
- Frozen build on any other OS (the Linux one-file build, .deb, .rpm,
  AppImage, .tar.gz): Deno is NOT bundled. A ``deno`` on PATH is used if
  present. Otherwise a copy downloaded earlier to the app data folder is
  used. Otherwise the pinned version is downloaded to
  ``<APP_DATA_DIR>/deno/<DENO_VERSION>/deno`` (on Linux
  ``~/.config/YT-DLP Studio/deno/2.9.8/deno``). The app folder is never
  used, because /opt is owned by root, the AppImage is read-only and a
  one-file build runs from a temporary folder.
- Source run: a copy in ``<project_root>/deno/`` is used, else a ``deno``
  on PATH, else the pinned version is downloaded to ``<project_root>/deno/``.

Every download is checked against a pinned SHA-256 before the binary is
kept. A failed download is never fatal: the app starts without Deno, and
non-YouTube sites still work.
"""

import hashlib
import hmac
import os
import platform
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from .logger import get_logger

logger = get_logger()

DENO_VERSION = "2.9.8"

_RELEASE_BASE = f"https://github.com/denoland/deno/releases/download/v{DENO_VERSION}"

_DENO_URLS = {
    ("Windows", "AMD64"): f"{_RELEASE_BASE}/deno-x86_64-pc-windows-msvc.zip",
    ("Linux", "x86_64"): f"{_RELEASE_BASE}/deno-x86_64-unknown-linux-gnu.zip",
    ("Darwin", "x86_64"): f"{_RELEASE_BASE}/deno-x86_64-apple-darwin.zip",
    ("Darwin", "arm64"): f"{_RELEASE_BASE}/deno-aarch64-apple-darwin.zip",
}

# SHA-256 of each release zip for DENO_VERSION, from the digests GitHub
# publishes for the v2.9.8 release assets. The Windows value matches
# DENO_SHA256 in .github/workflows/release.yml. Change these together with
# DENO_VERSION.
_DENO_SHA256 = {
    ("Windows", "AMD64"): "cba84b26e0df5ae7f74fc66b86a95b866872a86292ebd84fa1e959927edd93bf",
    ("Linux", "x86_64"): "e890975bc2549807bbcc0b584ffafda72cc7c93349dd99c80483dd784f6c4609",
    ("Darwin", "x86_64"): "4b2f5edd2639b7470f034238b321d7002d8dfb4726d8558f52c17afac370eb2c",
    ("Darwin", "arm64"): "9f0bf660393da2eaff044cdc7444cb08c73f235849b61d224d825a194ce7c98e",
}

# The release zips are about 40 MB and the binary inside about 120 MB.
# The limits stop a broken or hostile response from filling the disk.
_MAX_ZIP_BYTES = 200 * 1024 * 1024
_MAX_BINARY_BYTES = 500 * 1024 * 1024
_CHUNK_SIZE = 1024 * 1024
# (connect, read) timeouts in seconds for the download request.
_TIMEOUT = (15, 60)


def _get_deno_binary_name() -> str:
    return "deno.exe" if platform.system() == "Windows" else "deno"


def _get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _has_bundled_deno() -> bool:
    """True only for the frozen Windows build, which bundles deno.exe."""
    return _is_frozen() and platform.system() == "Windows"


def get_app_data_deno_dir() -> Path:
    """Folder for the Deno binary that a frozen non-Windows build downloads.

    ``<APP_DATA_DIR>/deno/<DENO_VERSION>``. The folder is per user and
    writable. The version is part of the path, so a new pinned version
    is downloaded next to the old one and never mixed with it.
    """
    from .constants import APP_DATA_DIR

    return APP_DATA_DIR / "deno" / DENO_VERSION


def get_downloaded_deno_path() -> Path:
    """Full path of the downloaded Deno binary in the app data folder."""
    return get_app_data_deno_dir() / _get_deno_binary_name()


def _get_install_dir() -> Path:
    """Where a download goes: the app data folder when frozen, else the project."""
    if _is_frozen():
        return get_app_data_deno_dir()
    return _get_project_root() / "deno"


def _is_deno_available() -> bool:
    """True if a usable Deno already exists, so no download is needed."""
    if _has_bundled_deno():
        return True

    if _is_frozen():
        # Not bundled: a system deno first, then a copy downloaded earlier.
        if shutil.which("deno") is not None:
            return True
        return get_downloaded_deno_path().is_file()

    local = _get_project_root() / "deno" / _get_deno_binary_name()
    if local.exists():
        return True

    if shutil.which("deno") is not None:
        return True

    return False


def _download_verified_zip(url: str, expected_sha256: str, target_dir: Path) -> Path | None:
    """Download ``url`` into a temporary file in ``target_dir`` and verify it.

    The SHA-256 is computed while the file is written. Returns the path of
    the verified zip, or None on a checksum mismatch (the file is deleted).
    Raises on network or size errors; the caller deletes the file then.
    """
    import requests

    fd, tmp_name = tempfile.mkstemp(prefix=".deno-", suffix=".zip.part", dir=target_dir)
    hasher = hashlib.sha256()
    downloaded = 0
    try:
        with os.fdopen(fd, "wb") as f, requests.get(url, stream=True, timeout=_TIMEOUT) as response:
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=_CHUNK_SIZE):
                if not chunk:
                    continue
                downloaded += len(chunk)
                if downloaded > _MAX_ZIP_BYTES:
                    raise OSError(f"Deno download exceeds {_MAX_ZIP_BYTES} bytes")
                f.write(chunk)
                hasher.update(chunk)
    except BaseException:
        _remove_quietly(tmp_name)
        raise

    actual = hasher.hexdigest()
    if not hmac.compare_digest(actual, expected_sha256):
        logger.warning(
            f"Deno download failed the SHA-256 check (expected {expected_sha256}, got {actual}). "
            "The file was deleted."
        )
        _remove_quietly(tmp_name)
        return None
    return Path(tmp_name)


def _extract_binary(zip_path: Path, binary_name: str, binary_path: Path) -> None:
    """Extract only ``binary_name`` from the zip to ``binary_path``, atomically.

    The binary is written to a temporary file in the same folder, made
    executable, and then renamed. A reader never sees a half-written file.
    """
    with zipfile.ZipFile(zip_path) as zf:
        try:
            info = zf.getinfo(binary_name)
        except KeyError:
            raise OSError(f"{binary_name} not found in the Deno archive") from None
        if info.file_size > _MAX_BINARY_BYTES:
            raise OSError(f"{binary_name} in the Deno archive exceeds {_MAX_BINARY_BYTES} bytes")

        fd, tmp_name = tempfile.mkstemp(prefix=".deno-", suffix=".part", dir=binary_path.parent)
        try:
            with os.fdopen(fd, "wb") as out, zf.open(info) as src:
                shutil.copyfileobj(src, out, _CHUNK_SIZE)
            if platform.system() != "Windows":
                # The binary must be executable. It lives in a per-user folder
                # and only the same user runs it, so 0o700 (rwx------) is enough.
                os.chmod(tmp_name, 0o700)
            os.replace(tmp_name, binary_path)
        except BaseException:
            _remove_quietly(tmp_name)
            raise


def _remove_quietly(path: str | Path) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


def ensure_deno_installed() -> Path | None:
    """
    Ensure Deno is available. Downloads it on first run if missing.

    Returns the path to the newly downloaded binary, or None if no download
    was needed, the platform is unsupported, or the download failed.
    Failure is non-fatal: the app still works without Deno (YouTube may
    lose formats). This call blocks while it downloads, so run it on a
    background thread (see src/app.py).
    """
    if _is_deno_available():
        return None

    system = platform.system()
    machine = platform.machine()
    url = _DENO_URLS.get((system, machine))
    expected_sha256 = _DENO_SHA256.get((system, machine))

    if url is None or expected_sha256 is None:
        logger.warning(
            f"No Deno auto-install available for {system}/{machine}. Install manually from https://deno.land"
        )
        return None

    binary_name = _get_deno_binary_name()

    zip_path = None
    try:
        target_dir = _get_install_dir()
        target_dir.mkdir(parents=True, exist_ok=True)
        binary_path = target_dir / binary_name

        logger.info(f"Deno not found. Downloading v{DENO_VERSION} from {url} to {target_dir}")
        logger.info("This is a one-time setup (about 40 MB).")

        zip_path = _download_verified_zip(url, expected_sha256, target_dir)
        if zip_path is None:
            logger.warning("Deno was not installed. App will work, but some YouTube formats may be unavailable.")
            return None

        _extract_binary(zip_path, binary_name, binary_path)

        logger.info(f"Deno installed at: {binary_path}")
        return binary_path

    except Exception as e:
        logger.warning(f"Deno auto-install failed: {e}. App will work, but some YouTube formats may be unavailable.")
        return None
    finally:
        if zip_path is not None:
            _remove_quietly(zip_path)
