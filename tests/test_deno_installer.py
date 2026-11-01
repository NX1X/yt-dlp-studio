"""Unit tests for the Deno installer helper.

These tests cover URL selection per platform, binary-name resolution,
availability detection and the download path. None of them touch the
network: requests is replaced by a fake that serves an in-memory zip, and
the app data folder is a pytest tmp_path.
"""

from __future__ import annotations

import hashlib
import io
import logging
import os
import stat
import sys
import threading
import zipfile

import pytest

from src.backend.yt_dlp_wrapper import YtDlpWrapper
from src.utils import deno_installer


@pytest.mark.parametrize(
    "system,machine,expected_in_url",
    [
        ("Windows", "AMD64", "windows-msvc.zip"),
        ("Linux", "x86_64", "linux-gnu.zip"),
        ("Darwin", "x86_64", "apple-darwin.zip"),
        ("Darwin", "arm64", "aarch64-apple-darwin.zip"),
    ],
)
def test_deno_urls_cover_supported_platforms(system, machine, expected_in_url):
    url = deno_installer._DENO_URLS[(system, machine)]
    assert expected_in_url in url
    assert deno_installer.DENO_VERSION in url


def test_deno_urls_pin_to_release_tag():
    """Every URL must point at the release tag for the pinned version."""
    expected_prefix = f"https://github.com/denoland/deno/releases/download/v{deno_installer.DENO_VERSION}/"
    for url in deno_installer._DENO_URLS.values():
        assert url.startswith(expected_prefix), url


def test_unsupported_platform_lookup_returns_none():
    assert deno_installer._DENO_URLS.get(("Plan9", "v9")) is None


def test_binary_name_per_platform(monkeypatch):
    monkeypatch.setattr(deno_installer.platform, "system", lambda: "Windows")
    assert deno_installer._get_deno_binary_name() == "deno.exe"

    monkeypatch.setattr(deno_installer.platform, "system", lambda: "Linux")
    assert deno_installer._get_deno_binary_name() == "deno"

    monkeypatch.setattr(deno_installer.platform, "system", lambda: "Darwin")
    assert deno_installer._get_deno_binary_name() == "deno"


def test_is_deno_available_true_for_frozen_windows(monkeypatch):
    """The frozen Windows EXE bundles deno.exe, so nothing is downloaded."""
    monkeypatch.setattr(deno_installer.sys, "frozen", True, raising=False)
    monkeypatch.setattr(deno_installer.platform, "system", lambda: "Windows")
    monkeypatch.setattr(deno_installer.shutil, "which", lambda name: None)
    assert deno_installer._is_deno_available() is True


def test_is_deno_available_frozen_linux_is_not_assumed(monkeypatch, tmp_path):
    """The frozen Linux build bundles no Deno, so it must not claim one."""
    monkeypatch.setattr(deno_installer.sys, "frozen", True, raising=False)
    monkeypatch.setattr(deno_installer.platform, "system", lambda: "Linux")
    monkeypatch.setattr(deno_installer.shutil, "which", lambda name: None)
    monkeypatch.setattr(deno_installer, "get_app_data_deno_dir", lambda: tmp_path / "deno" / "v")
    assert deno_installer._is_deno_available() is False


def test_is_deno_available_finds_local_binary(monkeypatch, tmp_path):
    monkeypatch.setattr(deno_installer.sys, "frozen", False, raising=False)
    monkeypatch.setattr(deno_installer.platform, "system", lambda: "Linux")
    monkeypatch.setattr(deno_installer, "_get_project_root", lambda: tmp_path)

    deno_dir = tmp_path / "deno"
    deno_dir.mkdir()
    (deno_dir / "deno").write_text("#!/bin/sh\nexit 0\n")

    assert deno_installer._is_deno_available() is True


def test_is_deno_available_falls_back_to_path(monkeypatch, tmp_path):
    monkeypatch.setattr(deno_installer.sys, "frozen", False, raising=False)
    monkeypatch.setattr(deno_installer.platform, "system", lambda: "Linux")
    monkeypatch.setattr(deno_installer, "_get_project_root", lambda: tmp_path)
    monkeypatch.setattr(deno_installer.shutil, "which", lambda name: "/usr/bin/deno")

    assert deno_installer._is_deno_available() is True


def test_is_deno_available_returns_false_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(deno_installer.sys, "frozen", False, raising=False)
    monkeypatch.setattr(deno_installer.platform, "system", lambda: "Linux")
    monkeypatch.setattr(deno_installer, "_get_project_root", lambda: tmp_path)
    monkeypatch.setattr(deno_installer.shutil, "which", lambda name: None)

    assert deno_installer._is_deno_available() is False


def test_ensure_deno_installed_skips_when_available(monkeypatch):
    monkeypatch.setattr(deno_installer, "_is_deno_available", lambda: True)
    # Should short-circuit before consulting platform/URL maps.
    assert deno_installer.ensure_deno_installed() is None


def test_ensure_deno_installed_returns_none_for_unsupported_platform(monkeypatch):
    monkeypatch.setattr(deno_installer, "_is_deno_available", lambda: False)
    monkeypatch.setattr(deno_installer.platform, "system", lambda: "Plan9")
    monkeypatch.setattr(deno_installer.platform, "machine", lambda: "v9")

    # No URL match, no exception, just a warning + None.
    assert deno_installer.ensure_deno_installed() is None


# ---------------------------------------------------------------------------
# Download path: frozen builds, app data folder, checksum, permissions
# ---------------------------------------------------------------------------

FAKE_BINARY = b"\x7fELF fake deno binary"


def _make_zip(member: str = "deno", data: bytes = FAKE_BINARY) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(member, data)
    return buf.getvalue()


class _FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        for i in range(0, len(self._payload), chunk_size):
            yield self._payload[i : i + chunk_size]


class _FakeRequests:
    """Stands in for the requests module. Records every URL asked for."""

    def __init__(self, payload: bytes | None = None, error: Exception | None = None):
        self.payload = payload
        self.error = error
        self.calls: list[str] = []

    def get(self, url, stream=False, timeout=None):
        self.calls.append(url)
        assert stream is True
        assert timeout is not None
        if self.error is not None:
            raise self.error
        return _FakeResponse(self.payload)


@pytest.fixture
def linux_frozen(monkeypatch, tmp_path):
    """A frozen Linux x86_64 build, no deno on PATH, empty app data folder."""
    deno_dir = tmp_path / "appdata" / "deno" / deno_installer.DENO_VERSION
    monkeypatch.setattr(deno_installer.sys, "frozen", True, raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.setattr(deno_installer.platform, "system", lambda: "Linux")
    monkeypatch.setattr(deno_installer.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(deno_installer.shutil, "which", lambda name: None)
    monkeypatch.setattr(deno_installer, "get_app_data_deno_dir", lambda: deno_dir)
    # The project root of a frozen run is the read-only bundle: never write there.
    monkeypatch.setattr(deno_installer, "_get_project_root", lambda: tmp_path / "project")
    YtDlpWrapper.reset_deno_cache()
    yield deno_dir
    YtDlpWrapper.reset_deno_cache()


def _use_fake_requests(monkeypatch, fake):
    monkeypatch.setitem(sys.modules, "requests", fake)


def _pin_linux_hash(monkeypatch, payload: bytes):
    monkeypatch.setitem(deno_installer._DENO_SHA256, ("Linux", "x86_64"), hashlib.sha256(payload).hexdigest())


def test_frozen_windows_uses_bundle_without_download(monkeypatch):
    monkeypatch.setattr(deno_installer.sys, "frozen", True, raising=False)
    monkeypatch.setattr(deno_installer.platform, "system", lambda: "Windows")
    monkeypatch.setattr(deno_installer.platform, "machine", lambda: "AMD64")
    fake = _FakeRequests(payload=b"")
    _use_fake_requests(monkeypatch, fake)

    assert deno_installer.ensure_deno_installed() is None
    assert fake.calls == []


def test_frozen_linux_with_system_deno_does_not_download(monkeypatch, linux_frozen):
    monkeypatch.setattr(deno_installer.shutil, "which", lambda name: "/usr/bin/deno")
    fake = _FakeRequests(payload=b"")
    _use_fake_requests(monkeypatch, fake)

    assert deno_installer.ensure_deno_installed() is None
    assert fake.calls == []
    assert not linux_frozen.exists()
    assert YtDlpWrapper()._get_deno_location() == "/usr/bin/deno"


@pytest.mark.skipif(sys.platform == "win32", reason="Linux-only path; the wrapper looks for deno.exe on Windows")
def test_frozen_linux_downloads_to_app_data_and_wrapper_finds_it(monkeypatch, linux_frozen, tmp_path):
    payload = _make_zip()
    _pin_linux_hash(monkeypatch, payload)
    fake = _FakeRequests(payload=payload)
    _use_fake_requests(monkeypatch, fake)

    path = deno_installer.ensure_deno_installed()

    assert path == linux_frozen / "deno"
    assert fake.calls == [deno_installer._DENO_URLS[("Linux", "x86_64")]]
    assert path.read_bytes() == FAKE_BINARY
    # Only the binary is left behind: no zip, no temporary files.
    assert sorted(p.name for p in linux_frozen.iterdir()) == ["deno"]
    assert not (tmp_path / "project").exists()
    assert YtDlpWrapper()._get_deno_location() == str(path)


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
def test_downloaded_binary_is_executable(monkeypatch, linux_frozen):
    payload = _make_zip()
    _pin_linux_hash(monkeypatch, payload)
    _use_fake_requests(monkeypatch, _FakeRequests(payload=payload))

    path = deno_installer.ensure_deno_installed()

    assert stat.S_IMODE(path.stat().st_mode) == 0o700
    assert os.access(path, os.X_OK)


@pytest.mark.skipif(sys.platform == "win32", reason="Linux-only path; the wrapper looks for deno.exe on Windows")
def test_second_start_reuses_downloaded_copy(monkeypatch, linux_frozen):
    payload = _make_zip()
    _pin_linux_hash(monkeypatch, payload)
    first = _FakeRequests(payload=payload)
    _use_fake_requests(monkeypatch, first)
    assert deno_installer.ensure_deno_installed() is not None
    assert len(first.calls) == 1

    # Next start: a new process, so a fresh wrapper cache.
    YtDlpWrapper.reset_deno_cache()
    second = _FakeRequests(error=AssertionError("must not download again"))
    _use_fake_requests(monkeypatch, second)

    assert deno_installer.ensure_deno_installed() is None
    assert second.calls == []
    assert YtDlpWrapper()._get_deno_location() == str(linux_frozen / "deno")


def test_checksum_mismatch_keeps_no_binary(monkeypatch, linux_frozen, caplog):
    monkeypatch.setitem(deno_installer._DENO_SHA256, ("Linux", "x86_64"), "0" * 64)
    _use_fake_requests(monkeypatch, _FakeRequests(payload=_make_zip()))

    with caplog.at_level(logging.WARNING):
        assert deno_installer.ensure_deno_installed() is None

    assert list(linux_frozen.iterdir()) == []
    assert any("SHA-256" in r.getMessage() for r in caplog.records)
    assert deno_installer._is_deno_available() is False
    assert YtDlpWrapper()._get_deno_location() is None


def test_offline_download_failure_is_not_fatal(monkeypatch, linux_frozen, caplog):
    _use_fake_requests(monkeypatch, _FakeRequests(error=OSError("network unreachable")))

    with caplog.at_level(logging.WARNING):
        assert deno_installer.ensure_deno_installed() is None

    assert list(linux_frozen.iterdir()) == []
    assert any("Deno auto-install failed" in r.getMessage() for r in caplog.records)


def test_archive_without_binary_is_rejected(monkeypatch, linux_frozen):
    payload = _make_zip(member="../evil")
    _pin_linux_hash(monkeypatch, payload)
    _use_fake_requests(monkeypatch, _FakeRequests(payload=payload))

    assert deno_installer.ensure_deno_installed() is None
    assert list(linux_frozen.iterdir()) == []


def test_oversized_download_is_rejected(monkeypatch, linux_frozen):
    payload = _make_zip()
    _pin_linux_hash(monkeypatch, payload)
    monkeypatch.setattr(deno_installer, "_MAX_ZIP_BYTES", 10)
    _use_fake_requests(monkeypatch, _FakeRequests(payload=payload))

    assert deno_installer.ensure_deno_installed() is None
    assert list(linux_frozen.iterdir()) == []


def test_source_run_still_downloads_to_project_folder(monkeypatch, tmp_path):
    monkeypatch.setattr(deno_installer.sys, "frozen", False, raising=False)
    monkeypatch.setattr(deno_installer.platform, "system", lambda: "Linux")
    monkeypatch.setattr(deno_installer.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(deno_installer.shutil, "which", lambda name: None)
    monkeypatch.setattr(deno_installer, "_get_project_root", lambda: tmp_path)
    app_data = tmp_path / "appdata"
    monkeypatch.setattr(deno_installer, "get_app_data_deno_dir", lambda: app_data)
    payload = _make_zip()
    _pin_linux_hash(monkeypatch, payload)
    _use_fake_requests(monkeypatch, _FakeRequests(payload=payload))

    path = deno_installer.ensure_deno_installed()

    assert path == tmp_path / "deno" / "deno"
    assert path.read_bytes() == FAKE_BINARY
    assert not app_data.exists()


def test_every_url_has_a_pinned_sha256():
    assert set(deno_installer._DENO_SHA256) == set(deno_installer._DENO_URLS)
    for digest in deno_installer._DENO_SHA256.values():
        assert len(digest) == 64
        int(digest, 16)


def test_app_data_deno_dir_is_versioned_under_app_data():
    from src.utils.constants import APP_DATA_DIR

    assert deno_installer.get_app_data_deno_dir() == APP_DATA_DIR / "deno" / deno_installer.DENO_VERSION


def test_background_thread_does_not_block_and_survives_failure(monkeypatch):
    """The startup thread returns at once, and a failure never escapes it."""
    from src import app as app_module

    release = threading.Event()

    def slow_failing_install():
        release.wait(5)
        raise RuntimeError("boom")

    monkeypatch.setattr(app_module, "ensure_deno_installed", slow_failing_install)
    thread = app_module.start_deno_install_thread()
    assert thread.daemon is True
    assert thread.is_alive()  # still "downloading": the caller was not blocked
    release.set()
    thread.join(5)
    assert not thread.is_alive()


def test_background_thread_resets_wrapper_cache_after_download(monkeypatch, tmp_path):
    from src import app as app_module

    monkeypatch.setattr(YtDlpWrapper, "_deno_cache", None)
    monkeypatch.setattr(YtDlpWrapper, "_deno_cache_checked", True)  # early lookup cached "not found"
    monkeypatch.setattr(app_module, "ensure_deno_installed", lambda: tmp_path / "deno")

    app_module.start_deno_install_thread().join(5)

    assert YtDlpWrapper._deno_cache_checked is False
