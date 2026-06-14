"""Unit tests for the Deno installer helper.

These tests target the pure logic of `deno_installer` - URL selection per
platform, binary-name resolution, and availability detection. None of them
touch the network; the actual download path is exercised manually in CI.
"""

from __future__ import annotations

import pytest

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


def test_is_deno_available_returns_true_when_frozen(monkeypatch):
    """Inside a PyInstaller bundle Deno is shipped in _MEIPASS, so we
    optimistically claim it's available and skip the local lookup."""
    monkeypatch.setattr(deno_installer.sys, "frozen", True, raising=False)
    assert deno_installer._is_deno_available() is True


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
