# Update Service - Internal Engineering Notes

Internal continuation notes for the auto-update feature. Read this before
resuming work on the updater. Last updated: 2026-05-17.

---

## Status: shipped this round

The following is implemented, tested (tests/test_update_checker.py, 23
passing), and on `main`'s working tree:

- Owner casing fixed (`GITHUB_OWNER = "NX1X"`).
- `_select_asset()` returns the full asset; `release_info` now carries real
  `size` and `digest` (fixes the old "Unknown size" bug).
- SHA-256 integrity verification in `download_update()` using GitHub's
  server-side asset `digest`. Mismatch deletes the file; missing digest
  degrades to "saved, run manually" and never auto-launches.
- Non-blocking `UpdateCheckThread` (no more UI freeze on the Settings tab).
- `AppConfig` gained `check_updates_on_startup`, `skipped_update_version`,
  `last_update_check`.
- Opt-in silent startup check (24h throttle, respects skipped version,
  silent on failure).
- "Skip This Version" button in `UpdateDialog`.
- Robust networking: shared `requests.Session`, descriptive User-Agent,
  retry/backoff on 5xx, explicit 403 rate-limit handling.
- Translation keys added for both `en` and `he`.

### CI / release interaction (verified)

GitHub computes `digest` server-side for every release asset, so any release
cut after this change verifies with no workflow change. Pre-change releases
(`v0.1.0`, `v0.1.1`) may lack a digest and will safely degrade to the
manual-run warning. No change to `.github/workflows/release.yml` is required
for the chosen "GitHub asset digest" approach.

---

## OPEN DECISION - pick this up when resuming

There is no real installer. `YT-DLP Studio.exe` is a portable one-file
PyInstaller binary, and the documented distribution is "extract the ZIP and
run". Launching the downloaded exe opens the new version as a *separate*
portable copy; it does not replace the running/installed one. The user ends
up with two copies. `UpdateDialog` copy ("run the installer", "this will
close the application") oversells what actually happens.

This is a pre-existing limitation, not introduced by the verification work.

### Options (decide before further work)

1. Leave as-is. Functional, wording imprecise.
2. Honesty fix (small, copy-only): reword the `en`/`he` strings so the flow
   reads as "download the new version" rather than "run the installer /
   replace your install". No logic change. Touch points:
   `msg_download_verified_install`, `msg_installer_saved`,
   `msg_installer_confirmation`, related dialog titles in
   `src/utils/translations.py`.
3. Real self-replace: an updater shim that swaps the running exe on next
   launch. Bigger, riskier, separate work. Needs design (rename-on-exit vs
   helper process, handling the portable-vs-extracted-ZIP cases, antivirus
   implications). Not scoped yet.

User was unavailable to decide; deferred. Recommended default if still
undecided: option 2 (low risk, removes the misleading wording) and scope
option 3 separately.

---

## Pointers

- Backend: `src/backend/update_checker.py`
- UI: `src/ui/update_dialog.py`, wiring in `src/ui/settings_tab.py` and
  `src/ui/main_window.py`
- Config model: `src/models/app_config.py`
- Strings: `src/utils/translations.py` (keep `en` and `he` in sync)
- Tests: `tests/test_update_checker.py`
