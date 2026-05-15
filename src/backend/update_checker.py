"""
Auto-Update System for YT-DLP Studio.

Checks GitHub releases for new versions and facilitates updates.
Repository: https://github.com/NX1X/yt-dlp-studio
"""

import requests
from packaging import version

from ..utils.constants import APP_VERSION
from ..utils.logger import get_logger

logger = get_logger()

# GitHub API configuration
GITHUB_OWNER = "nx1x"
GITHUB_REPO = "yt-dlp-studio"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"


class UpdateChecker:
    """
    Checks for application updates from GitHub releases.

    Compares current version with latest GitHub release.
    """

    def __init__(self):
        """Initialize UpdateChecker."""
        self.current_version = APP_VERSION
        logger.debug(f"UpdateChecker initialized with version {self.current_version}")

    def check_for_updates(self, timeout: int = 10) -> tuple[bool, dict | None]:
        """
        Check if a new version is available on GitHub.

        Args:
            timeout: Request timeout in seconds

        Returns:
            Tuple of (update_available: bool, release_info: dict or None)

        Example:
            >>> checker = UpdateChecker()
            >>> available, info = checker.check_for_updates()
            >>> if available:
            >>>     print(f"New version: {info['version']}")
        """
        logger.info("Checking for updates...")

        try:
            # Make request to GitHub API
            response = requests.get(
                GITHUB_API_URL, timeout=timeout, headers={"Accept": "application/vnd.github.v3+json"}
            )

            if response.status_code != 200:
                logger.error(f"GitHub API returned status {response.status_code}")
                return False, None

            release_data = response.json()

            # Extract version from tag_name (e.g., "v1.7.0" -> "1.7.0")
            tag_name = release_data.get("tag_name", "")
            latest_version = tag_name.lstrip("v")

            # Compare versions
            is_newer = self._is_version_newer(latest_version, self.current_version)

            if is_newer:
                logger.info(f"Update available: {latest_version} (current: {self.current_version})")

                # Extract relevant information
                release_info = {
                    "version": latest_version,
                    "tag_name": tag_name,
                    "name": release_data.get("name", f"Version {latest_version}"),
                    "body": release_data.get("body", ""),
                    "published_at": release_data.get("published_at", ""),
                    "html_url": release_data.get("html_url", ""),
                    "download_url": self._get_download_url(release_data),
                    "assets": release_data.get("assets", []),
                }

                return True, release_info
            else:
                logger.info(f"No update available. Current version {self.current_version} is up to date.")
                return False, None

        except requests.exceptions.Timeout:
            logger.error("Update check timed out")
            return False, None
        except requests.exceptions.RequestException as e:
            logger.error(f"Update check failed: {e}")
            return False, None
        except Exception as e:
            logger.error(f"Unexpected error during update check: {e}")
            return False, None

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

    def _get_download_url(self, release_data: dict) -> str | None:
        """
        Extract the appropriate download URL from release assets.

        Args:
            release_data: GitHub release data

        Returns:
            Download URL for the installer or None
        """
        assets = release_data.get("assets", [])

        # Look for Windows installer (.exe)
        for asset in assets:
            name = asset.get("name", "").lower()
            if name.endswith(".exe") or "setup" in name or "installer" in name:
                return asset.get("browser_download_url")

        # Look for zip file
        for asset in assets:
            name = asset.get("name", "").lower()
            if name.endswith(".zip"):
                return asset.get("browser_download_url")

        # Fallback to first asset
        if assets:
            return assets[0].get("browser_download_url")

        # Last resort: use release page URL
        return release_data.get("html_url")

    def download_update(self, download_url: str, output_path: str, progress_callback=None) -> bool:
        """
        Download update file from URL.

        Args:
            download_url: URL to download from
            output_path: Path to save downloaded file
            progress_callback: Optional callback for progress updates (receives bytes_downloaded, total_bytes)

        Returns:
            True if download successful, False otherwise
        """
        logger.info(f"Downloading update from: {download_url}")

        try:
            response = requests.get(download_url, stream=True, timeout=30)

            if response.status_code != 200:
                logger.error(f"Download failed with status {response.status_code}")
                return False

            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress_callback and total_size > 0:
                            progress_callback(downloaded, total_size)

            logger.info(f"Update downloaded successfully to: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Download error: {e}")
            return False

    def get_current_version(self) -> str:
        """
        Get current application version.

        Returns:
            Current version string
        """
        return self.current_version

    def get_github_repo_url(self) -> str:
        """
        Get GitHub repository URL.

        Returns:
            Repository URL
        """
        return f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}"

    def get_latest_release_url(self) -> str:
        """
        Get URL to latest GitHub release page.

        Returns:
            Latest release page URL
        """
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

        # Basic cleanup
        formatted = body.strip()

        # Truncate if too long
        if len(formatted) > max_length:
            formatted = formatted[:max_length] + "..."

        return formatted
