"""
Tests for UpdateChecker (Qt-free, headless).

Run with: pytest tests/test_update_checker.py -v
"""

import hashlib
from pathlib import Path

import pytest

from src.backend.update_checker import (
    DownloadResult,
    UpdateChecker,
    UpdateCheckResult,
    _normalize_digest,
)


class FakeResponse:
    """Minimal stand-in for a requests.Response."""

    def __init__(self, status_code=200, json_data=None, headers=None, chunks=None):
        self.status_code = status_code
        self._json = json_data or {}
        self.headers = headers or {}
        self._chunks = chunks or []

    def json(self):
        return self._json

    def iter_content(self, chunk_size=8192):
        yield from self._chunks


class FakeSession:
    """Records the last GET and returns a queued response."""

    def __init__(self, response):
        self._response = response
        self.last_url = None
        self.last_kwargs = None

    def get(self, url, **kwargs):
        self.last_url = url
        self.last_kwargs = kwargs
        return self._response


class TestNormalizeDigest:
    def test_strips_sha256_prefix(self):
        h = "a" * 64
        assert _normalize_digest(f"sha256:{h}") == h

    def test_accepts_bare_hex(self):
        h = "b" * 64
        assert _normalize_digest(h) == h

    def test_case_insensitive(self):
        assert _normalize_digest("SHA256:" + "A" * 64) == "a" * 64

    @pytest.mark.parametrize("bad", [None, "", "sha256:xyz", "deadbeef", "sha512:" + "a" * 64])
    def test_rejects_invalid(self, bad):
        assert _normalize_digest(bad) == ""


class TestVersionCompare:
    def test_newer(self):
        c = UpdateChecker()
        assert c._is_version_newer("2.0.0", "1.9.9") is True

    def test_same_or_older(self):
        c = UpdateChecker()
        assert c._is_version_newer("1.0.0", "1.0.0") is False
        assert c._is_version_newer("1.0.0", "1.2.0") is False

    def test_invalid_is_safe(self):
        c = UpdateChecker()
        assert c._is_version_newer("not-a-version", "1.0.0") is False


class TestSelectAsset:
    def test_prefers_exe_with_size_and_digest(self):
        c = UpdateChecker()
        data = {
            "assets": [
                {"name": "notes.zip", "browser_download_url": "u-zip", "size": 5},
                {
                    "name": "YT-DLP-Studio-Setup.exe",
                    "browser_download_url": "u-exe",
                    "size": 123,
                    "digest": "sha256:" + "c" * 64,
                },
            ]
        }
        asset = c._select_asset(data)
        assert asset.url == "u-exe"
        assert asset.size == 123
        assert asset.digest == "c" * 64

    def test_falls_back_to_zip_then_first(self):
        c = UpdateChecker()
        assert c._select_asset({"assets": [{"name": "x.zip", "browser_download_url": "z"}]}).url == "z"
        assert c._select_asset({"assets": [{"name": "x.bin", "browser_download_url": "b"}]}).url == "b"
        assert c._select_asset({"assets": []}) is None


class TestCheckForUpdates:
    def test_rate_limited(self):
        c = UpdateChecker()
        c._session = FakeSession(FakeResponse(status_code=403, headers={"X-RateLimit-Remaining": "0"}))
        result = c.check_for_updates()
        assert isinstance(result, UpdateCheckResult)
        assert result.error == "rate_limited"
        assert result.update_available is False

    def test_update_available_populates_size_and_digest(self):
        c = UpdateChecker()
        c.current_version = "0.0.1"
        digest = "d" * 64
        c._session = FakeSession(
            FakeResponse(
                json_data={
                    "tag_name": "v9.9.9",
                    "html_url": "https://example/release",
                    "assets": [
                        {
                            "name": "YT-DLP-Studio.exe",
                            "browser_download_url": "https://example/dl.exe",
                            "size": 999,
                            "digest": f"sha256:{digest}",
                        }
                    ],
                }
            )
        )
        result = c.check_for_updates()
        assert result.update_available is True
        assert result.release_info["version"] == "9.9.9"
        assert result.release_info["size"] == 999
        assert result.release_info["digest"] == digest
        assert result.release_info["download_url"] == "https://example/dl.exe"

    def test_up_to_date(self):
        c = UpdateChecker()
        c.current_version = "9.9.9"
        c._session = FakeSession(FakeResponse(json_data={"tag_name": "v0.0.1", "assets": []}))
        result = c.check_for_updates()
        assert result.update_available is False
        assert result.error is None


class TestDownloadUpdate:
    def _payload(self):
        data = b"installer-bytes-" * 32
        return data, hashlib.sha256(data).hexdigest()

    def test_success_on_matching_digest(self, tmp_path: Path):
        data, digest = self._payload()
        c = UpdateChecker()
        c._session = FakeSession(FakeResponse(headers={"content-length": str(len(data))}, chunks=[data]))
        out = tmp_path / "app.exe"
        result = c.download_update("https://x/app.exe", str(out), expected_digest=f"sha256:{digest}")
        assert isinstance(result, DownloadResult)
        assert result.success is True
        assert out.exists()
        assert out.read_bytes() == data

    def test_mismatch_deletes_file(self, tmp_path: Path):
        data, _ = self._payload()
        c = UpdateChecker()
        c._session = FakeSession(FakeResponse(headers={"content-length": str(len(data))}, chunks=[data]))
        out = tmp_path / "app.exe"
        result = c.download_update("https://x/app.exe", str(out), expected_digest="sha256:" + "0" * 64)
        assert result.success is False
        assert result.error == "verify_failed"
        assert not out.exists()

    def test_no_digest_keeps_file_but_untrusted(self, tmp_path: Path):
        data, _ = self._payload()
        c = UpdateChecker()
        c._session = FakeSession(FakeResponse(headers={"content-length": str(len(data))}, chunks=[data]))
        out = tmp_path / "app.exe"
        result = c.download_update("https://x/app.exe", str(out), expected_digest=None)
        assert result.success is False
        assert result.error == "no_digest"
        assert out.exists()

    def test_http_error(self, tmp_path: Path):
        c = UpdateChecker()
        c._session = FakeSession(FakeResponse(status_code=404))
        result = c.download_update("https://x/app.exe", str(tmp_path / "a.exe"), expected_digest="x")
        assert result.success is False
        assert result.error == "download_failed"
