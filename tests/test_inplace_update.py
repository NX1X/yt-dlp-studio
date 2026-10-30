"""In-place updates: installed copies update through the installer, portable copies do not.

Covers install detection (install.ini written by packaging/installer.iss),
which release asset each kind of copy picks, and how the dialog starts the
verified download.
"""

from __future__ import annotations

import pytest

from src.backend import update_checker as uc
from src.backend.update_checker import UpdateChecker, is_installed_copy

# The asset list a 0.3.0 release publishes (see the release workflow).
RELEASE_030 = [
    {"name": "yt-dlp-studio-v0.3.0-Linux.tar.gz", "browser_download_url": "u-linux"},
    {"name": "yt-dlp-studio-v0.3.0-Windows.zip", "browser_download_url": "u-zip"},
    {"name": "YT-DLP.Studio.exe", "browser_download_url": "u-portable"},
    {"name": "YT-DLP-Studio-Setup-0.3.0.exe", "browser_download_url": "u-setup"},
]
# Releases before 0.3.0 have no installer.
RELEASE_021 = [a for a in RELEASE_030 if "Setup" not in a["name"]]


# ---------- install detection ----------


def test_installed_when_marker_says_inno(tmp_path):
    (tmp_path / "install.ini").write_text("[install]\nkind=inno\nversion=0.3.0\n", encoding="utf-8")
    assert is_installed_copy(tmp_path) is True


@pytest.mark.parametrize("content", [None, "[install]\nkind=other\n", "", "kind = innosetup\n"])
def test_not_installed_without_a_valid_marker(tmp_path, content):
    if content is not None:
        (tmp_path / "install.ini").write_text(content, encoding="utf-8")
    assert is_installed_copy(tmp_path) is False


def test_running_from_source_is_never_installed(monkeypatch):
    monkeypatch.delattr("sys.frozen", raising=False)
    assert is_installed_copy() is False


# ---------- asset choice ----------


def test_installed_copy_picks_the_installer():
    assert UpdateChecker._select_windows_asset(RELEASE_030, installed=True)["browser_download_url"] == "u-setup"


def test_portable_copy_never_picks_the_installer():
    # The installer would turn a portable user into an installed one silently.
    assert UpdateChecker._select_windows_asset(RELEASE_030, installed=False)["browser_download_url"] == "u-portable"


def test_installed_copy_falls_back_when_release_has_no_installer():
    assert UpdateChecker._select_windows_asset(RELEASE_021, installed=True)["browser_download_url"] == "u-portable"


def test_select_asset_uses_install_detection(monkeypatch):
    monkeypatch.setattr("src.backend.update_checker.os.name", "nt")
    monkeypatch.setattr(uc, "is_installed_copy", lambda exe_dir=None: True)
    assert UpdateChecker()._select_asset({"assets": RELEASE_030}).url == "u-setup"
    monkeypatch.setattr(uc, "is_installed_copy", lambda exe_dir=None: False)
    assert UpdateChecker()._select_asset({"assets": RELEASE_030}).url == "u-portable"


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("YT-DLP-Studio-Setup-0.3.0.exe", "installer"),
        ("yt-dlp-studio-setup.exe", "installer"),
        ("YT-DLP.Studio.exe", "portable"),
        ("yt-dlp-studio-v0.3.0-Windows.zip", "archive"),
        ("yt-dlp-studio-v0.3.0-Linux.tar.gz", "archive"),
        ("", "archive"),
    ],
)
def test_update_kind(name, kind):
    assert UpdateChecker.update_kind_for(name) == kind


# ---------- the dialog starts the verified download ----------


@pytest.fixture
def dialog(qtbot):
    from src.ui.update_dialog import UpdateDialog

    dlg = UpdateDialog({"version": "0.3.0", "download_url": "u", "update_kind": "installer"})
    qtbot.addWidget(dlg)
    return dlg


@pytest.fixture
def launched(monkeypatch):
    """Capture Popen calls and the app quit, instead of running anything."""
    calls = {"popen": [], "quit": 0}

    def fake_popen(argv, **kwargs):
        calls["popen"].append((list(argv), kwargs))

    monkeypatch.setattr("src.ui.update_dialog.subprocess.Popen", fake_popen)
    from PySide6.QtWidgets import QApplication

    monkeypatch.setattr(QApplication.instance(), "quit", lambda: calls.__setitem__("quit", calls["quit"] + 1))
    return calls


def test_installer_runs_silently_and_relaunches(dialog, launched):
    dialog._run_installer_silent(r"C:\Users\u\Downloads\YT-DLP-Studio-Setup-0.3.0.exe")
    argv, kwargs = launched["popen"][0]
    assert argv == [
        r"C:\Users\u\Downloads\YT-DLP-Studio-Setup-0.3.0.exe",
        "/SILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        "/LAUNCH=yes",
    ]
    assert "shell" not in kwargs  # list argv, never a shell
    assert launched["quit"] == 1


def test_portable_update_starts_the_new_copy_without_installer_args(dialog, launched):
    dialog._launch_and_quit([r"C:\Users\u\Downloads\YT-DLP.Studio.exe"])
    argv, _ = launched["popen"][0]
    assert argv == [r"C:\Users\u\Downloads\YT-DLP.Studio.exe"]
    assert launched["quit"] == 1


def test_launch_failure_shows_an_error_and_keeps_the_app_open(dialog, monkeypatch):
    def boom(argv, **kwargs):
        raise OSError("blocked")

    shown = []
    monkeypatch.setattr("src.ui.update_dialog.subprocess.Popen", boom)
    monkeypatch.setattr("src.ui.update_dialog.QMessageBox.critical", lambda *a, **k: shown.append(a))
    quits = []
    from PySide6.QtWidgets import QApplication

    monkeypatch.setattr(QApplication.instance(), "quit", lambda: quits.append(1))
    dialog._launch_and_quit(["setup.exe", "/SILENT"])
    assert shown, "an error box must be shown"
    assert not quits, "the app must stay open when the update could not start"
