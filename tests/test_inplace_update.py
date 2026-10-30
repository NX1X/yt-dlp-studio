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

import hashlib  # noqa: E402

from src.backend.update_checker import safe_asset_filename  # noqa: E402

PAYLOAD = b"verified-installer-bytes" * 64
PAYLOAD_DIGEST = hashlib.sha256(PAYLOAD).hexdigest()


@pytest.fixture(autouse=True)
def no_modal_boxes(monkeypatch):
    """No test may ever block on a modal QMessageBox; record them instead."""
    shown = []
    for kind in ("critical", "warning", "information"):
        monkeypatch.setattr(
            f"src.ui.update_dialog.QMessageBox.{kind}",
            lambda *a, _k=kind, **kw: shown.append(_k),
        )
    return shown


@pytest.fixture
def dialog(qtbot):
    from src.ui.update_dialog import UpdateDialog

    dlg = UpdateDialog({"version": "0.3.0", "download_url": "u", "update_kind": "installer", "digest": PAYLOAD_DIGEST})
    qtbot.addWidget(dlg)
    return dlg


@pytest.fixture
def setup_file(tmp_path):
    f = tmp_path / "YT-DLP-Studio-Setup-0.3.0.exe"
    f.write_bytes(PAYLOAD)
    return str(f)


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


def test_installer_runs_silently_and_relaunches(dialog, setup_file, launched):
    dialog._run_installer_silent(setup_file)
    argv, kwargs = launched["popen"][0]
    assert argv == [setup_file, "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/LAUNCH=yes"]
    assert "shell" not in kwargs  # list argv, never a shell
    assert launched["quit"] == 1


def test_portable_update_starts_the_new_copy_without_installer_args(dialog, setup_file, launched):
    dialog._launch_and_quit([setup_file])
    argv, _ = launched["popen"][0]
    assert argv == [setup_file]
    assert launched["quit"] == 1


def test_file_swapped_after_verification_is_not_started(dialog, setup_file, launched, no_modal_boxes):
    """The file sits in Downloads while the user reads the question; re-hash before running it."""
    with open(setup_file, "ab") as f:
        f.write(b"tampered")
    dialog._launch_and_quit([setup_file, "/SILENT"])
    assert launched["popen"] == []
    assert launched["quit"] == 0
    assert "critical" in no_modal_boxes


def test_no_digest_never_starts_anything(qtbot, setup_file, launched):
    from src.ui.update_dialog import UpdateDialog

    dlg = UpdateDialog({"version": "0.3.0", "download_url": "u", "update_kind": "installer"})
    qtbot.addWidget(dlg)
    dlg._launch_and_quit([setup_file])
    assert launched["popen"] == []


def test_launch_failure_shows_an_error_and_keeps_the_app_open(dialog, setup_file, monkeypatch, no_modal_boxes):
    def boom(argv, **kwargs):
        raise OSError("blocked")

    monkeypatch.setattr("src.ui.update_dialog.subprocess.Popen", boom)
    quits = []
    from PySide6.QtWidgets import QApplication

    monkeypatch.setattr(QApplication.instance(), "quit", lambda: quits.append(1))
    dialog._launch_and_quit([setup_file, "/SILENT"])
    assert "critical" in no_modal_boxes
    assert not quits, "the app must stay open when the update could not start"


# ---------- asset names from the API are never used as paths unchecked ----------


@pytest.mark.parametrize(
    "name",
    ["YT-DLP-Studio-Setup-0.3.0.exe", "YT-DLP.Studio.exe", "yt-dlp-studio-v0.3.0-Windows.zip"],
)
def test_plain_asset_names_are_kept(name):
    assert safe_asset_filename(name) == name


@pytest.mark.parametrize(
    "name",
    ["../x.exe", "..\\x.exe", "C:\\x.exe", "/etc/x", "a.exe:stream", "..", ".", "", None, "x.exe ", "x.", "a\nb.exe"],
)
def test_unsafe_asset_names_are_refused(name):
    assert safe_asset_filename(name) is None


# ---------- download hardening ----------


class _Resp:
    def __init__(self, chunks, url, length=None):
        self.status_code = 200
        self.url = url
        self.headers = {"content-length": str(length if length is not None else sum(map(len, chunks)))}
        self._chunks = chunks

    def iter_content(self, chunk_size=None):
        yield from self._chunks


class _Session:
    def __init__(self, resp):
        self.resp = resp
        self.calls = 0

    def get(self, *a, **k):
        self.calls += 1
        return self.resp


GH = "https://github.com/NX1X/yt-dlp-studio/releases/download/v0.3.0/YT-DLP-Studio-Setup-0.3.0.exe"


@pytest.mark.parametrize(
    "url", ["http://github.com/a.exe", "https://evil.example/a.exe", "https://github.com.evil.io/a.exe"]
)
def test_download_refuses_unexpected_hosts(tmp_path, url):
    c = UpdateChecker()
    c._session = _Session(_Resp([PAYLOAD], url))
    out = tmp_path / "a.exe"
    result = c.download_update(url, str(out), expected_digest=PAYLOAD_DIGEST)
    assert result.success is False
    assert c._session.calls == 0, "nothing may be fetched from an unexpected host"
    assert not out.exists()


def test_download_refuses_a_redirect_off_github(tmp_path):
    c = UpdateChecker()
    c._session = _Session(_Resp([PAYLOAD], "https://evil.example/landed.exe"))
    out = tmp_path / "a.exe"
    assert c.download_update(GH, str(out), expected_digest=PAYLOAD_DIGEST).success is False
    assert not out.exists()


def test_verified_download_is_written_via_part_file(tmp_path):
    c = UpdateChecker()
    c._session = _Session(_Resp([PAYLOAD], GH))
    out = tmp_path / "a.exe"
    assert c.download_update(GH, str(out), expected_digest=PAYLOAD_DIGEST).success is True
    assert out.read_bytes() == PAYLOAD
    assert not (tmp_path / "a.exe.part").exists()


def test_mismatch_leaves_no_file_under_the_real_name(tmp_path):
    c = UpdateChecker()
    c._session = _Session(_Resp([PAYLOAD], GH))
    out = tmp_path / "a.exe"
    assert c.download_update(GH, str(out), expected_digest="0" * 64).error == "verify_failed"
    assert not out.exists() and not (tmp_path / "a.exe.part").exists()


def test_oversized_download_is_aborted(tmp_path):
    c = UpdateChecker()
    # The server claims 10 bytes but sends far more than the 1 MiB slack.
    c._session = _Session(_Resp([b"x" * (2 * 1024 * 1024)], GH, length=10))
    out = tmp_path / "a.exe"
    assert c.download_update(GH, str(out), expected_digest=PAYLOAD_DIGEST).success is False
    assert not out.exists() and not (tmp_path / "a.exe.part").exists()
