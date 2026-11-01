# Contributing to YT-DLP Studio

Thank you for your interest in YT-DLP Studio. This guide explains how to set up a development environment, which code standards apply, and how to submit a change.

For more detail on the code, see the [Development Guide](docs/DEVELOPMENT.md) and the [Architecture](docs/ARCHITECTURE.md) document.

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By taking part, you agree to follow it.

## Development setup

### Prerequisites

- Python 3.11 or later.
- Git.
- FFmpeg, for full functionality. The Windows release includes it. On Linux and macOS, install it separately.
- A working Qt stack. The PySide6 wheels provide it on supported platforms.

### Clone and install

1. Clone the repository:

   ```bash
   git clone https://github.com/NX1X/yt-dlp-studio.git
   cd yt-dlp-studio
   ```

2. Create a virtual environment:

   ```bash
   python -m venv .venv
   ```

3. Activate it:

   ```bash
   # Windows (PowerShell):
   .\.venv\Scripts\Activate.ps1
   # macOS / Linux:
   source .venv/bin/activate
   ```

4. Install the runtime and development dependencies. These are hash-pinned, the same set that CI uses:

   ```bash
   pip install --require-hashes -r requirements/dev.txt
   ```

5. Install the pre-commit hooks (recommended):

   ```bash
   pre-commit install
   ```

If you change dependencies in `pyproject.toml`, regenerate the lock files with `scripts/relock.sh`. The script needs uv. It applies the 14-day cooldown and resolves for every platform.

### Start the app

```bash
python launcher.py
```

## Workflow

1. Create a branch from `main`:

   ```bash
   git checkout -b feat/short-description
   ```

2. Make your change. Keep each pull request focused on one feature or one fix.
3. Run the quality checks:

   ```bash
   ruff check src/ tests/ launcher.py
   ruff format --check src/ tests/ launcher.py
   black --check src/ tests/ launcher.py
   pytest tests/ -v
   ```

4. Add an entry to `CHANGELOG.md` under `## [Unreleased]`.
5. Commit with a [Conventional Commits](https://www.conventionalcommits.org/) message. Examples:

   ```
   feat: add subtitle language picker
   fix: handle 4K-only formats without audio merge
   docs: clarify FFmpeg installation on Linux
   ci: bump actions/checkout to v6
   chore: regenerate translations
   ```

6. Push the branch and open a pull request against `main`.
7. Fill in the pull request template. CI must pass before the merge.

## Code standards

| Topic | Rule |
|-------|------|
| Python version | 3.11 or later |
| Line length | 120 characters |
| Linter | `ruff check` |
| Formatter | `black` (and `ruff format`) |
| Type hints | Required on all new public functions |
| Tests | Required for new features and bug fixes |
| GUI framework | PySide6 (Qt for Python) |
| String quotes | Use what `black` produces. Do not fight the formatter. |

`vendor/yt_dlp_engine/` is a vendored copy of yt-dlp. Linting and formatting exclude it. Do not reformat it. If you must patch upstream behavior, add a comment that explains why, and keep the diff small.

## Tests

- Tests are in `tests/`. Run them with `pytest`.
- GUI tests use `pytest-qt`. For headless runs, set `QT_QPA_PLATFORM=offscreen`.
- On a Linux machine without a display, run the GUI tests with `xvfb-run`:

  ```bash
  xvfb-run --auto-servernum pytest tests/ -v
  ```

- To get a coverage report, run:

  ```bash
  pytest tests/ -v --cov=src --cov-report=term-missing
  ```

## Changelog

- Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
- Categories: **Added**, **Changed**, **Deprecated**, **Removed**, **Fixed**, **Security**.
- Add new entries under `## [Unreleased]`. At release time, `python scripts/sync_version.py` renames that section to `## [<version>] - <date>`.

## Versioning

- The project uses [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`).
- Versions below 1.0.0 are pre-stable.
- `__version__` in `src/__init__.py` is the single source of truth. `pyproject.toml` reads it dynamically.
- After a version bump, run `python scripts/sync_version.py`. It updates `packaging/version_info.txt` (the Windows EXE metadata) and the `CHANGELOG.md` header.
- The release workflow publishes a release when `__version__` has no tag yet. `CHANGELOG.md` must have a matching `## [<version>]` entry. Do not push version tags by hand.

## Pull request checklist

- [ ] The branch is up to date with `main`.
- [ ] The description explains what changed and why, and links related issues.
- [ ] `CHANGELOG.md` has an entry under `## [Unreleased]`.
- [ ] Tests are added or updated.
- [ ] `ruff check` and `ruff format --check` pass.
- [ ] `pytest tests/ -v` passes locally.
- [ ] No secrets, API keys or large binaries are committed.

## Report bugs and request features

- **Bugs:** open an issue with the **Bug Report** template.
- **Features:** open an issue with the **Feature Request** template.
- **Security vulnerabilities:** do not use public issues. See [SECURITY.md](SECURITY.md).

## License

By contributing, you agree that your contributions are licensed under the project's [Apache License 2.0](LICENSE).
