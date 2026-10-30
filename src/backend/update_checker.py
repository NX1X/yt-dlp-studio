"""
Auto-Update System for YT-DLP Studio.

Checks GitHub releases for new versions and facilitates updates.
Repository: https://github.com/NX1X/yt-dlp-studio

The checker is intentionally Qt-free so it can be unit tested headlessly and
driven from a background QThread (see src/ui/update_dialog.py).
"""

import hashlib
import hmac
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import requests
from packaging import version
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..utils.constants import APP_VERSION
from ..utils.logger import get_logger

logger = get_logger()

# GitHub API configuration
GITHUB_OWNER = "NX1X"
GITHUB_REPO = "yt-dlp-studio"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

# GitHub asks API clients to send a descriptive User-Agent.
USER_AGENT = f"YT-DLP-Studio/{APP_VERSION} (+https://github.com/{GITHUB_OWNER}/{GITHUB_REPO})"

# Streaming hash/IO chunk size.
_CHUNK_SIZE = 8192


@dataclass
class UpdateCheckResult:
    """Outcome of an update check.

    Attributes:
        update_available: True if a newer release exists.
        release_info: Release metadata when an update is available, else None.
        error: A short machine-readable error reason when the check could not
            complete (e.g. ``"network"``, ``"rate_limited"``), else None.
    """

    update_available: bool = False
    release_info: dict | None = None
    error: str | None = None


@dataclass
class DownloadResult:
    """Outcome of an installer download + integrity verification.

    Attributes:
        success: True only if the file downloaded *and* passed verification.
        file_path: Path to the verified file (empty on failure).
        error: Reason on failure: ``"download_failed"``, ``"verify_failed"``,
            or ``"no_digest"`` (GitHub did not publish a digest to verify
            against, so the file was not trusted for auto-launch).
    """

    success: bool = False
    file_path: str = ""
    error: str | None = None
    expected_digest: str = ""
    actual_digest: str = ""


@dataclass
class _Asset:
    url: str
    size: int = 0
    digest: str = ""  # normalized lowercase sha256 hex, or "" if unknown
    extras: dict = field(default_factory=dict)


# The Windows installer (packaging/installer.iss) is named
# YT-DLP-Studio-Setup-<version>.exe and writes install.ini next to the EXE.
_SETUP_ASSET_RE = re.compile(r"yt-dlp-studio-setup(-[A-Za-z0-9._+]+)?\.exe", re.IGNORECASE)

# Hosts an update may be downloaded from (GitHub release assets redirect to
# the githubusercontent CDNs). Anything else is refused before any byte is
# written.
_ALLOWED_DOWNLOAD_HOSTS = frozenset(
    {"github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com"}
)
# Hard cap when the release does not publish a size.
_MAX_DOWNLOAD_BYTES = 1024 * 1024 * 1024


def _is_allowed_download_url(url: str | None) -> bool:
    """True for an https URL on a GitHub release-asset host."""
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url or "")
    except ValueError:
        return False
    return parsed.scheme == "https" and (parsed.hostname or "").lower() in _ALLOWED_DOWNLOAD_HOSTS


def safe_asset_filename(name: str | None) -> str | None:
    """Return ``name`` if it is a plain file name, else None.

    The release asset name comes from the GitHub API and becomes a path under
    the Downloads folder. Refuse anything that is not a single, ordinary file
    name: path separators, drive letters or NTFS streams (":"), "." / "..",
    control characters, or leading/trailing spaces and dots.
    """
    if not name:
        return None
    if name != name.strip() or name.endswith("."):
        return None
    if name in (".", "..") or any(sep in name for sep in ("/", "\\", ":")):
        return None
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in name):
        return None
    return name


def sha256_of_file(path: str) -> str:
    """Hex SHA-256 of a file, read in chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK_SIZE), b""):
            h.update(chunk)
    return h.hexdigest()


def is_installed_copy(exe_dir: Path | None = None) -> bool:
    """Return True when this app runs from a copy installed by the Windows installer.

    The installer writes ``install.ini`` with ``kind=inno`` next to the EXE. A
    portable copy (the ZIP or the standalone EXE) has no such file, and running
    from source never counts as installed.

    Args:
        exe_dir: Folder to check. Defaults to the folder of the running EXE.
    """
    if exe_dir is None:
        if os.name != "nt" or not getattr(sys, "frozen", False):
            return False
        exe_dir = Path(sys.executable).resolve().parent
    marker = exe_dir / "install.ini"
    try:
        with open(marker, encoding="utf-8", errors="replace") as f:
            text = f.read(4096)
    except OSError:
        return False
    return re.search(r"^\s*kind\s*=\s*inno\s*$", text, re.IGNORECASE | re.MULTILINE) is not None


def _normalize_digest(raw: str | None) -> str:
    """Normalize a GitHub asset digest to a bare lowercase sha256 hex string.

    GitHub returns digests as ``"sha256:<hex>"``. Returns "" for anything that
    is not a recognizable sha256 digest so callers can treat it as "unknown".
    """
    if not raw:
        return ""
    value = raw.strip().lower()
    if value.startswith("sha256:"):
        value = value[len("sha256:") :]
    # A valid sha256 hex digest is exactly 64 hex chars.
    if len(value) == 64 and all(c in "0123456789abcdef" for c in value):
        return value
    return ""


class UpdateChecker:
    """
    Checks for application updates from GitHub releases.

    Compares current version with latest GitHub release and verifies the
    integrity of any downloaded installer against GitHub's published digest.
    """

    def __init__(self):
        """Initialize UpdateChecker."""
        self.current_version = APP_VERSION
        self._session = self._build_session()
        logger.debug(f"UpdateChecker initialized with version {self.current_version}")

    @staticmethod
    def _build_session() -> requests.Session:
        """Build a requests Session with a descriptive UA and retry/backoff."""
        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})
        # Note: allowed_methods is intentionally left at its default (which
        # already includes GET) for compatibility with older urllib3 where
        # the kwarg was named method_whitelist.
        retry = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=0.5,
            # Retry transient server/proxy errors only. 403 (rate limit) and
            # 404 are handled explicitly and must not be retried.
            status_forcelist=(500, 502, 503, 504),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        # HTTPS only: every endpoint this checker calls (GitHub API and
        # release-asset downloads) is HTTPS, so plain HTTP gets no retries.
        session.mount("https://", adapter)
        return session

    def check_for_updates(self, timeout: int = 10) -> UpdateCheckResult:
        """
        Check if a new version is available on GitHub.

        Args:
            timeout: Request timeout in seconds

        Returns:
            UpdateCheckResult

        Example:
            >>> result = UpdateChecker().check_for_updates()
            >>> if result.update_available:
            >>>     print(result.release_info["version"])
        """
        logger.info("Checking for updates...")

        try:
            response = self._session.get(
                GITHUB_API_URL,
                timeout=timeout,
                headers={"Accept": "application/vnd.github+json"},
            )

            if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
                logger.warning("GitHub API rate limit exceeded")
                return UpdateCheckResult(error="rate_limited")

            if response.status_code != 200:
                logger.error(f"GitHub API returned status {response.status_code}")
                return UpdateCheckResult(error="network")

            release_data = response.json()

            # Extract version from tag_name (e.g., "v1.7.0" -> "1.7.0")
            tag_name = release_data.get("tag_name", "")
            latest_version = tag_name.lstrip("v")

            if not self._is_version_newer(latest_version, self.current_version):
                logger.info(f"No update available. {self.current_version} is up to date.")
                return UpdateCheckResult(update_available=False)

            logger.info(f"Update available: {latest_version} (current: {self.current_version})")

            asset = self._select_asset(release_data)
            release_info = {
                "version": latest_version,
                "tag_name": tag_name,
                "name": release_data.get("name", f"Version {latest_version}"),
                "body": release_data.get("body", ""),
                "published_at": release_data.get("published_at", ""),
                "html_url": release_data.get("html_url", ""),
                "download_url": asset.url if asset else release_data.get("html_url"),
                "asset_name": asset.extras.get("name", "") if asset else "",
                "update_kind": self.update_kind_for(asset.extras.get("name", "")) if asset else "archive",
                "size": asset.size if asset else 0,
                "digest": asset.digest if asset else "",
                "assets": release_data.get("assets", []),
            }
            return UpdateCheckResult(update_available=True, release_info=release_info)

        except requests.exceptions.Timeout:
            logger.exception("Update check timed out")
            return UpdateCheckResult(error="timeout")
        except requests.exceptions.RequestException:
            logger.exception("Update check failed")
            return UpdateCheckResult(error="network")
        except Exception:
            logger.exception("Unexpected error during update check")
            return UpdateCheckResult(error="unknown")

    def _is_version_newer(self, latest: str, current: str) -> bool:
        """
        Compare version strings.

        Args:
            latest: Latest version string
            current: Current version string

        Returns:
            True if latest is newer than current
        """
        try:
            return version.parse(latest) > version.parse(current)
        except Exception as e:
            logger.warning(f"Version comparison error: {e}")
            return False

    def _select_asset(self, release_data: dict) -> _Asset | None:
        """
        Select the most appropriate downloadable asset for the current OS.

        On Windows the priority is installer/.exe -> .zip -> first asset.
        On Linux it is the Linux archive (name contains "linux" or ends in
        .tar.gz / .AppImage) -> first asset. The full asset is returned
        (URL, size and GitHub-published digest) so callers can show an
        accurate size and verify integrity.

        Returns:
            _Asset, or None if the release has no matching asset.
        """
        assets = release_data.get("assets", []) or []
        if os.name != "nt":
            chosen = self._select_linux_asset(assets)
        else:
            chosen = self._select_windows_asset(assets, installed=is_installed_copy())
        return self._make_asset(chosen) if chosen else None

    @staticmethod
    def _make_asset(asset: dict) -> _Asset:
        return _Asset(
            url=asset.get("browser_download_url", ""),
            size=int(asset.get("size", 0) or 0),
            digest=_normalize_digest(asset.get("digest")),
            extras=asset,
        )

    @staticmethod
    def _select_linux_asset(assets: list[dict]) -> dict | None:
        """Prefer a Linux archive; never a Windows .exe/.msi (useless on Linux)."""
        for asset in assets:
            name = asset.get("name", "").lower()
            if "linux" in name or name.endswith((".tar.gz", ".tgz", ".appimage")):
                return asset
        for asset in assets:
            if not asset.get("name", "").lower().endswith((".exe", ".msi")):
                return asset
        return None

    @staticmethod
    def _select_windows_asset(assets: list[dict], installed: bool = False) -> dict | None:
        """Pick the Windows asset that matches how this copy was installed.

        An installed copy updates through the installer
        (YT-DLP-Studio-Setup-<version>.exe), which replaces it in place. A
        portable copy gets the standalone EXE, then the ZIP. Releases before
        0.3.0 have no installer, so an installed copy falls back to the
        portable choice there.
        """
        if installed:
            for asset in assets:
                if _SETUP_ASSET_RE.fullmatch(asset.get("name", "")):
                    return asset
        for asset in assets:
            name = asset.get("name", "")
            if name.lower().endswith(".exe") and not _SETUP_ASSET_RE.fullmatch(name):
                return asset
        for asset in assets:
            if asset.get("name", "").lower().endswith(".zip"):
                return asset
        # No known Windows artifact: offer nothing rather than an arbitrary
        # first asset (which could be the installer, a checksum file or a
        # script).
        return None

    @staticmethod
    def update_kind_for(asset_name: str) -> str:
        """Classify an update asset: "installer", "portable" or "archive"."""
        name = asset_name or ""
        if _SETUP_ASSET_RE.fullmatch(name):
            return "installer"
        if name.lower().endswith(".exe"):
            return "portable"
        return "archive"

    def download_update(
        self,
        download_url: str,
        output_path: str,
        expected_digest: str | None = None,
        progress_callback=None,
    ) -> DownloadResult:
        """
        Download an update file and verify its SHA-256 integrity.

        The hash is computed in the same streaming pass used to write the
        file (no second read). The file is only reported as a success if the
        computed digest matches ``expected_digest``. On mismatch the partial
        file is deleted so a corrupt/tampered installer can never be launched.

        Args:
            download_url: URL to download from
            output_path: Path to save downloaded file
            expected_digest: GitHub-published digest (``"sha256:<hex>"`` or bare
                hex). If absent/unverifiable the download is treated as
                untrusted (``error="no_digest"``).
            progress_callback: Optional callback(bytes_downloaded, total_bytes)

        Returns:
            DownloadResult
        """
        import os

        logger.info(f"Downloading update from: {download_url}")
        want = _normalize_digest(expected_digest)

        part_path = output_path + ".part"
        try:
            if not _is_allowed_download_url(download_url):
                logger.error(f"Refusing update download from an unexpected URL: {download_url}")
                return DownloadResult(success=False, error="download_failed")

            response = self._session.get(download_url, stream=True, timeout=30)

            if response.status_code != 200:
                logger.error(f"Download failed with status {response.status_code}")
                return DownloadResult(success=False, error="download_failed")
            if not _is_allowed_download_url(getattr(response, "url", None) or download_url):
                logger.error(f"Update download was redirected to an unexpected URL: {response.url}")
                return DownloadResult(success=False, error="download_failed")

            total_size = int(response.headers.get("content-length", 0))
            limit = total_size + 1024 * 1024 if total_size > 0 else _MAX_DOWNLOAD_BYTES
            downloaded = 0
            hasher = hashlib.sha256()

            # Write to a .part file; only a verified (or knowingly unverified)
            # download gets the real name, so a broken or partial download
            # never looks like a runnable installer.
            with open(part_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=_CHUNK_SIZE):
                    if chunk:
                        downloaded += len(chunk)
                        if downloaded > limit:
                            raise OSError(f"update download exceeds the expected size ({limit} bytes)")
                        f.write(chunk)
                        hasher.update(chunk)
                        if progress_callback and total_size > 0:
                            progress_callback(downloaded, total_size)

            actual = hasher.hexdigest()

            if not want:
                # GitHub did not publish a digest we can trust. Keep the file
                # (the user can still install it manually) but refuse to
                # auto-launch it.
                logger.warning("No verifiable digest published for this release; download is unverified")
                os.replace(part_path, output_path)
                return DownloadResult(
                    success=False,
                    file_path=output_path,
                    error="no_digest",
                    actual_digest=actual,
                )

            if not hmac.compare_digest(actual, want):
                logger.error(f"Integrity check FAILED (expected {want}, got {actual}); deleting file")
                try:
                    os.remove(part_path)
                except OSError:
                    pass
                return DownloadResult(
                    success=False,
                    error="verify_failed",
                    expected_digest=want,
                    actual_digest=actual,
                )

            os.replace(part_path, output_path)
            logger.info(f"Update downloaded and verified (sha256={actual}): {output_path}")
            return DownloadResult(
                success=True,
                file_path=output_path,
                expected_digest=want,
                actual_digest=actual,
            )

        except Exception:
            logger.exception("Download error")
            try:
                os.remove(part_path)
            except OSError:
                pass
            return DownloadResult(success=False, error="download_failed")

    def get_current_version(self) -> str:
        """Get current application version."""
        return self.current_version

    def get_github_repo_url(self) -> str:
        """Get GitHub repository URL."""
        return f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}"

    def get_latest_release_url(self) -> str:
        """Get URL to latest GitHub release page."""
        return f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

    @staticmethod
    def format_release_notes(body: str, max_length: int = 500) -> str:
        """
        Format release notes for display.

        Args:
            body: Raw markdown body from GitHub
            max_length: Maximum length to display

        Returns:
            Formatted release notes
        """
        if not body:
            return "No release notes available."

        formatted = body.strip()

        if len(formatted) > max_length:
            formatted = formatted[:max_length] + "..."

        return formatted
