<!--
Thanks for contributing to YT-DLP Studio!
Please fill out the sections below so reviewers can move quickly.
-->

## Description

<!-- What does this PR do? Why is the change needed? -->

Closes #

## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Refactor / internal cleanup (no user-facing change)
- [ ] Documentation update
- [ ] CI / build / tooling change
- [ ] Dependency update / security patch

## Areas Touched

- [ ] UI (`src/ui/`)
- [ ] Backend / download engine (`src/backend/`)
- [ ] Models (`src/models/`)
- [ ] Utilities (`src/utils/`)
- [ ] Translations / i18n
- [ ] Tests (`tests/`)
- [ ] Build / packaging (`packaging/`, `launcher.py`)
- [ ] CI workflows (`.github/workflows/`)
- [ ] Vendored `vendor/yt_dlp_engine/` (please justify in description)

## How Has This Been Tested?

<!--
Describe the tests that you ran. Include the OS + Python version, and whether
the GUI was exercised. Paste pytest output if relevant.
-->

- [ ] Ran `ruff check src/ tests/ launcher.py`
- [ ] Ran `ruff format --check src/ tests/ launcher.py`
- [ ] Ran `black --check src/ tests/ launcher.py`
- [ ] Ran `pytest tests/ -v`
- [ ] Manually exercised the affected UI flow on Windows
- [ ] Manually exercised the affected UI flow on Linux

## Screenshots / Recordings

<!-- Drop screenshots or short clips for any visible UI change. -->

## Checklist

- [ ] Branch is rebased on / merged with the latest `main`
- [ ] PR title follows [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `ci:`, `chore:`, ...)
- [ ] [`CHANGELOG.md`](../CHANGELOG.md) updated under the next version header
- [ ] Tests added or updated
- [ ] No secrets, API keys, or credentials are committed
- [ ] No large binaries committed (FFmpeg, Deno, exes are downloaded by CI)
- [ ] Public APIs/functions have type hints
- [ ] Code of Conduct ([`CODE_OF_CONDUCT.md`](../CODE_OF_CONDUCT.md)) acknowledged
