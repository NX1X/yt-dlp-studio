"""Consistency checks for the Windows installer (packaging/installer.iss).

The installer is only compiled and exercised on a Windows CI runner. These
checks run everywhere and catch drift between the Inno Setup script, the app
and the CI test script before a Windows build is needed.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ISS = ROOT / "packaging" / "installer.iss"


def _iss_text() -> str:
    return ISS.read_bytes().decode("utf-8-sig")


def test_iss_is_utf8_with_bom():
    """Inno Setup reads a script as UTF-8 only with a BOM; the Hebrew prompt needs it."""
    assert ISS.read_bytes().startswith(b"\xef\xbb\xbf")


def test_app_user_model_id_matches_app():
    from src.utils.constants import APP_USER_MODEL_ID

    match = re.search(r'#define AppUserModelID "([^"]+)"', _iss_text())
    assert match, "AppUserModelID define missing from installer.iss"
    assert match.group(1) == APP_USER_MODEL_ID


def test_app_id_is_fixed_and_matches_ci_test():
    """AppId is the upgrade identity; the CI test checks the matching registry key."""
    iss_id = re.search(r"^AppId=\{\{([0-9A-F-]{36})\}", _iss_text(), re.MULTILINE)
    assert iss_id, "AppId must be a fixed GUID"
    ps1 = (ROOT / "scripts" / "test_installer.ps1").read_text(encoding="utf-8")
    assert f'$AppId = "{{{iss_id.group(1)}}}"' in ps1


def test_per_user_install_without_admin():
    text = _iss_text()
    assert "PrivilegesRequired=lowest" in text
    assert re.search(r"^DefaultDirName=\{localappdata\}\\Programs\\", text, re.MULTILINE)


def test_installer_installs_the_portable_payload():
    """One payload: the installer ships the same one-file EXE as the portable download."""
    assert '#define SourceExe "..\\dist\\yt-dlp-studio.exe"' in _iss_text()


def test_uninstall_keeps_user_data_by_default():
    """Purge only on an explicit /PURGEDATA=yes or a Yes answer (the box defaults to No)."""
    text = _iss_text()
    assert "{param:PURGEDATA|no}" in text
    assert "MB_DEFBUTTON2" in text
    # Nothing in [UninstallDelete] may point at the user's data directory.
    section = text.split("[UninstallDelete]", 1)[1].split("[Code]", 1)[0]
    assert "userappdata" not in section


def test_app_data_dir_matches_installer():
    """The data directory the uninstaller protects must be the one the app writes to."""
    from src.utils.constants import APP_NAME

    assert '#define AppName "' + APP_NAME + '"' in _iss_text()
    assert "ExpandConstant('{userappdata}\\{#AppName}')" in _iss_text()


def test_installer_resets_pyinstaller_env_for_the_app_it_starts():
    # An update started from 0.3.0 or 0.3.1 passes the old app's PyInstaller
    # variables to the installer; the installer must neutralize them before it
    # relaunches the app.
    text = _iss_text()
    assert "SetEnvironmentVariableW@kernel32.dll stdcall" in text
    assert "SetEnvironmentVariable('PYINSTALLER_RESET_ENVIRONMENT', '1');" in text
    assert "function InitializeSetup: Boolean;" in text


def test_ci_reproduces_the_stale_env_update():
    ps1 = (ROOT / "scripts" / "test_installer.ps1").read_text(encoding="utf-8")
    assert "_PYI_APPLICATION_HOME_DIR" in ps1
    assert '"/LAUNCH=yes"' in ps1
