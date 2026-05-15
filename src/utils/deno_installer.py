"""
Deno auto-installer for YT-DLP Studio.

Downloads and installs the Deno JS runtime on first run if not present.
Deno is required by yt-dlp to solve YouTube's JS challenges and unlock
all available formats. Pinned to v2.6.10 to match the CI build.
"""

import os
import platform
import shutil
import sys
import zipfile
from pathlib import Path

from .logger import get_logger

logger = get_logger()

DENO_VERSION = "2.6.10"

_DENO_URLS = {
    (
        "Windows",
        "AMD64",
    ): f"https://github.com/denoland/deno/releases/download/v{DENO_VERSION}/deno-x86_64-pc-windows-msvc.zip",
    (
        "Linux",
        "x86_64",
    ): f"https://github.com/denoland/deno/releases/download/v{DENO_VERSION}/deno-x86_64-unknown-linux-gnu.zip",
    (
        "Darwin",
        "x86_64",
    ): f"https://github.com/denoland/deno/releases/download/v{DENO_VERSION}/deno-x86_64-apple-darwin.zip",
    (
        "Darwin",
        "arm64",
    ): f"https://github.com/denoland/deno/releases/download/v{DENO_VERSION}/deno-aarch64-apple-darwin.zip",
}


def _get_deno_binary_name() -> str:
    return "deno.exe" if platform.system() == "Windows" else "deno"


def _get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _is_deno_available() -> bool:
    if getattr(sys, "frozen", False):
        return True

    binary = _get_deno_binary_name()

    local = _get_project_root() / "deno" / binary
    if local.exists():
        return True

    if shutil.which("deno") is not None:
        return True

    return False


def ensure_deno_installed() -> Path | None:
    """
    Ensure Deno is available. Downloads it on first run if missing.

    Returns the path to the deno binary if installed/found, or None if
    the platform is unsupported or download failed. Failure is non-fatal —
    the app still works without Deno (just with limited YouTube formats).
    """
    if _is_deno_available():
        return None

    system = platform.system()
    machine = platform.machine()
    url = _DENO_URLS.get((system, machine))

    if url is None:
        logger.warning(
            f"No Deno auto-install available for {system}/{machine}. Install manually from https://deno.land"
        )
        return None

    target_dir = _get_project_root() / "deno"
    target_dir.mkdir(parents=True, exist_ok=True)
    binary_path = target_dir / _get_deno_binary_name()

    logger.info(f"Deno not found. Downloading v{DENO_VERSION} from {url}")
    logger.info("This is a one-time setup (~30MB) and runs only on first launch.")

    try:
        import requests

        zip_path = target_dir / "deno.zip"
        with requests.get(url, stream=True, timeout=60) as response:
            response.raise_for_status()
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)

        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(target_dir)

        zip_path.unlink()

        if system != "Windows":
            # The downloaded Deno binary must be executable to run. 0o755 is the
            # standard executable mode (rwxr-xr-x): owner-writable only, not
            # group/world-writable, so this is not an over-permissive mask.
            os.chmod(binary_path, 0o755)  # noqa: S103

        if not binary_path.exists():
            logger.error("Deno extraction completed but binary not found at expected path")
            return None

        logger.info(f"✓ Deno installed at: {binary_path}")
        return binary_path

    except Exception as e:
        logger.warning(f"Deno auto-install failed: {e}. App will work, but some YouTube formats may be unavailable.")
        return None
