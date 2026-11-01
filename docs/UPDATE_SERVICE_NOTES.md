# Update Service: Engineering Notes

Internal notes for the auto-update feature. Read them before you resume work on the updater.

- First written: 2026-05-17.
- Status section updated: 2026-11-01, against release 0.3.1 and `main`.

## Current status (0.3.1)

The open decision from 2026-05-17 (see below) is resolved. Release 0.3.0 added a real Windows installer and in-place updates. Release 0.3.1 added Linux packages.

How each copy updates (source: `src/backend/update_checker.py`, `src/ui/update_dialog.py`, `CHANGELOG.md`):

| Copy | How the app knows | What the update does |
|------|-------------------|----------------------|
| Windows installer copy | `install.ini` with `kind=inno` next to the EXE | Downloads the new installer, checks its SHA-256, runs it with `/SILENT /LAUNCH=yes`, and starts again. |
| Windows portable EXE or ZIP | No `install.ini` | Downloads the new portable EXE. The message says that it is a separate copy that does not replace the running one. |
| Linux .deb or .rpm | `install.ini` with `kind=deb` or `kind=rpm` in `/opt/yt-dlp-studio` | Downloads the new package and offers to open the download folder. The user opens the package with the software installer. |
| Linux AppImage | Detected as an AppImage | Downloads the new AppImage. The user makes it executable and starts it. |
| Linux archive (.tar.gz) | None of the above | Downloads the new archive. |

A portable copy never runs the installer silently. If the installer is offered to a portable copy, the app saves the file and does not run it.

## Shipped in the 2026-05-17 round

This work was implemented and tested (`tests/test_update_checker.py`, 23 tests passing at the time):

- Owner casing fixed (`GITHUB_OWNER = "NX1X"`).
- `_select_asset()` returns the full asset. `release_info` now carries the real `size` and `digest`. This fixes the old "Unknown size" bug.
- SHA-256 verification in `download_update()`, against the asset `digest` that GitHub computes on the server. A mismatch deletes the file. A missing digest falls back to "saved, run manually" and never starts the file automatically.
- Non-blocking `UpdateCheckThread`. The Settings tab no longer freezes during a check.
- `AppConfig` gained `check_updates_on_startup`, `skipped_update_version` and `last_update_check`.
- Opt-in silent check at startup. It runs at most once every 24 hours, respects the skipped version, and stays silent on failure.
- **Skip This Version** button in `UpdateDialog`.
- Robust networking: a shared `requests.Session`, a descriptive User-Agent, retry with backoff on 5xx responses, and explicit handling of 403 rate limits.
- Translation keys for both `en` and `he`.

### CI and release interaction (verified 2026-05-17)

GitHub computes `digest` on the server for every release asset. Any release cut after this change verifies without a workflow change. Older releases (`v0.1.0`, `v0.1.1`) may lack a digest. For those, the app falls back safely to the "run manually" warning. The "GitHub asset digest" approach needs no change to `.github/workflows/release.yml`.

## Resolved decision (history)

On 2026-05-17 there was no real installer. `YT-DLP Studio.exe` was a portable one-file PyInstaller binary, and the documented install was "extract the ZIP and run". Launching the downloaded EXE opened the new version as a *separate* portable copy. It did not replace the running copy, so the user ended up with two copies. The `UpdateDialog` text ("run the installer", "this will close the application") promised more than it did. This limitation existed before the verification work; that work did not cause it.

The options were:

1. Leave it as it is. It works, but the wording is imprecise.
2. Honesty fix (small, text only): reword the `en` and `he` strings so the flow reads as "download the new version", not "run the installer" or "replace your install". No logic change. Touch points at the time: `msg_download_verified_install`, `msg_installer_saved`, `msg_installer_confirmation` and the related dialog titles in `src/utils/translations.py`. Only `msg_installer_saved` still exists today.
3. Real self-replace: an updater shim that replaces the running EXE on the next launch. This is bigger, riskier, separate work. It needed a design: rename on exit or a helper process, the portable EXE and extracted ZIP cases, and antivirus implications. It was not scoped.

The owner was not available to decide, so the decision was deferred. The recommended default was option 2 (low risk, removes the misleading wording), with option 3 scoped separately.

Outcome: 0.3.0 did both 2 and 3 in a different form. The Inno Setup installer (`packaging/installer.iss`) gives the installed copy a real in-place update. Portable copies keep the separate-copy behavior, with honest wording (`msg_portable_update_ready`, `msg_portable_update_saved` in `src/utils/translations.py`).

## Pointers

- Backend: `src/backend/update_checker.py`
- UI: `src/ui/update_dialog.py`, wired in `src/ui/settings_tab.py` and `src/ui/main_window.py`
- Installer: `packaging/installer.iss`
- Linux packages: `packaging/linux/build_packages.sh`
- Config model: `src/models/app_config.py`
- Strings: `src/utils/translations.py` (keep `en` and `he` in sync)
- Tests: `tests/test_update_checker.py`, `tests/test_inplace_update.py`
