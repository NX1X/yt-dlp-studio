"""Linux packages: the AppImage, .deb and .rpm, and how each copy updates.

Covers install detection (APPIMAGE from the AppImage runtime, install.ini
written by packaging/linux/build_packages.sh), which release asset each kind
of copy picks, and the packaging script's invariants.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from src.backend.update_checker import UpdateChecker, linux_install_kind
from src.utils.translations import TRANSLATIONS

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "packaging" / "linux" / "build_packages.sh"

# The asset list a 0.3.1 release publishes (see the release workflow).
RELEASE_031 = [
    {"name": "YT-DLP-Studio-0.3.1-x86_64.AppImage", "browser_download_url": "u-appimage"},
    {"name": "YT-DLP-Studio-Setup-0.3.1.exe", "browser_download_url": "u-setup"},
    {"name": "yt-dlp-studio-0.3.1-1.x86_64.rpm", "browser_download_url": "u-rpm"},
    {"name": "yt-dlp-studio-v0.3.1-Linux.tar.gz", "browser_download_url": "u-tar"},
    {"name": "yt-dlp-studio-v0.3.1-Windows.zip", "browser_download_url": "u-zip"},
    {"name": "yt-dlp-studio_0.3.1_amd64.deb", "browser_download_url": "u-deb"},
]
# Releases before 0.3.1 have no Linux packages.
RELEASE_030 = [a for a in RELEASE_031 if not a["name"].endswith((".AppImage", ".deb", ".rpm"))]


# ---------- install detection ----------


def test_appimage_detected_from_runtime_env(tmp_path):
    assert linux_install_kind(tmp_path, environ={"APPIMAGE": "/home/u/YT.AppImage"}) == "appimage"


@pytest.mark.parametrize("kind", ["deb", "rpm"])
def test_package_detected_from_marker(tmp_path, kind):
    (tmp_path / "install.ini").write_text(f"[Install]\nkind={kind}\nversion=0.3.1\n", encoding="utf-8")
    assert linux_install_kind(tmp_path, environ={}) == kind


def test_tarball_copy_has_no_kind(tmp_path):
    assert linux_install_kind(tmp_path, environ={}) is None


def test_windows_marker_is_not_a_linux_kind(tmp_path):
    (tmp_path / "install.ini").write_text("[install]\nkind=inno\n", encoding="utf-8")
    assert linux_install_kind(tmp_path, environ={}) is None


def test_source_run_has_no_kind(monkeypatch):
    monkeypatch.setattr("src.backend.update_checker.os.name", "posix")
    monkeypatch.delattr("sys.frozen", raising=False)
    assert linux_install_kind() is None


# ---------- asset selection ----------


@pytest.mark.parametrize(
    ("kind", "url"),
    [("appimage", "u-appimage"), ("deb", "u-deb"), ("rpm", "u-rpm"), (None, "u-tar")],
)
def test_each_kind_picks_its_own_package(kind, url):
    assert UpdateChecker._select_linux_asset(RELEASE_031, kind=kind)["browser_download_url"] == url


@pytest.mark.parametrize("kind", ["appimage", "deb", "rpm", None])
def test_release_without_packages_falls_back_to_tarball(kind):
    assert UpdateChecker._select_linux_asset(RELEASE_030, kind=kind)["browser_download_url"] == "u-tar"


def test_tarball_copy_never_gets_a_package_or_exe():
    only_packages = [a for a in RELEASE_031 if a["name"].endswith((".deb", ".rpm", ".exe", ".zip"))]
    assert UpdateChecker._select_linux_asset(only_packages, kind=None) is None


def test_select_asset_uses_detected_kind(monkeypatch):
    monkeypatch.setattr("src.backend.update_checker.os.name", "posix")
    monkeypatch.setattr("src.backend.update_checker.linux_install_kind", lambda: "deb")
    assert UpdateChecker()._select_asset({"assets": RELEASE_031}).url == "u-deb"


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("YT-DLP-Studio-0.3.1-x86_64.AppImage", "appimage"),
        ("yt-dlp-studio_0.3.1_amd64.deb", "package"),
        ("yt-dlp-studio-0.3.1-1.x86_64.rpm", "package"),
        ("yt-dlp-studio-v0.3.1-Linux.tar.gz", "archive"),
    ],
)
def test_update_kind_for_linux_assets(name, kind):
    assert UpdateChecker.update_kind_for(name) == kind


@pytest.mark.parametrize("key", ["msg_download_verified_reveal_package", "msg_download_verified_reveal_appimage"])
def test_reveal_messages_exist_in_both_languages(key):
    for lang in ("en", "he"):
        assert "{path}" in TRANSLATIONS[lang][key]


# ---------- the packaging script ----------


def _script() -> str:
    return SCRIPT.read_text(encoding="utf-8")


@pytest.mark.skipif(os.name == "nt", reason="Windows file systems have no exec bit")
def test_script_is_executable():
    assert SCRIPT.stat().st_mode & 0o111


def test_tools_are_pinned_by_sha256():
    text = _script()
    for var in ("APPIMAGETOOL_SHA256", "APPIMAGE_RUNTIME_SHA256"):
        assert re.search(rf'^{var}="[0-9a-f]{{64}}"$', text, re.MULTILINE), var
    assert "sha256sum --check --strict" in text


def test_packages_write_the_marker_the_updater_reads():
    text = _script()
    assert 'stage_system_root "${root}" deb' in text
    assert 'stage_system_root "${root}" rpm' in text
    assert "kind=%s" in text


def test_rpm_never_strips_the_binary():
    # Stripping a PyInstaller one-file binary cuts off its appended archive.
    text = _script()
    assert "%global __os_install_post %{nil}" in text
    assert "%global debug_package %{nil}" in text
    assert "AutoReqProv:    no" in text


def test_no_package_script_deletes_user_data():
    text = _script()
    assert ".config" not in "".join(line for line in text.splitlines() if "rm " in line)


def test_asset_names_match_what_the_updater_selects():
    text = _script()
    assert "YT-DLP-Studio-${VERSION}-x86_64.AppImage" in text
    assert "${APP_ID}_${VERSION}_amd64.deb" in text
    assert "${APP_ID}-${VERSION}-1.x86_64.rpm" in text


def test_desktop_entry_and_icons_exist():
    linux = ROOT / "packaging" / "linux"
    assert (linux / "yt-dlp-studio.desktop").is_file()
    for size in (32, 48, 64, 128, 256):
        assert (linux / f"yt-dlp-studio-{size}.png").is_file()
