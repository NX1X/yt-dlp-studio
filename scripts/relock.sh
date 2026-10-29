#!/usr/bin/env bash
# Regenerate the hash-pinned lock files after changing dependencies in
# pyproject.toml or requirements/build-tools.in.
#
# Why this script exists: Renovate bumps the version bounds in pyproject.toml
# but does not regenerate these files, so the locks drift from the bounds. In
# 2026-09 the lock pinned PySide6 6.11.0 while pyproject.toml required
# >=6.11.2. tests/test_lock_consistency.py fails when that happens again.
#
# Rules this script enforces:
#   - --universal: resolve platform and Python-version markers for every
#     target. A lock compiled on Linux otherwise drops Windows-only packages
#     (colorama for pytest), and a lock compiled on 3.14 drops packages only
#     older Pythons need (tomli for PySide6 on 3.10). Either one makes
#     `pip install --require-hashes` fail on the affected CI runner.
#   - --python-version 3.10: the requires-python floor.
#   - --exclude-newer: the 14-day supply-chain cooldown, applied to every
#     package including transitive ones (Renovate's minimumReleaseAge only
#     covers the direct dependencies it bumps).
#   - Order: lock.txt first, then the files constrained by it.
#
# Usage: scripts/relock.sh            (cutoff = 14 days ago)
#        scripts/relock.sh 2026-09-30 (explicit cutoff date, UTC)
set -euo pipefail

cd "$(dirname "$0")/.."

if [ $# -ge 1 ]; then
  cutoff="$1T00:00:00Z"
else
  cutoff="$(date -u -d '14 days ago' +%Y-%m-%dT00:00:00Z)"
fi

common=(--universal --generate-hashes --python-version 3.10 --exclude-newer "$cutoff" --quiet)

echo "Cooldown cutoff: $cutoff"
uv pip compile pyproject.toml "${common[@]}" -o requirements/lock.txt
uv pip compile requirements/build-tools.in -c requirements/lock.txt "${common[@]}" -o requirements/build-tools.txt
uv pip compile pyproject.toml --extra dev -c requirements/lock.txt "${common[@]}" -o requirements/dev.txt

echo "Regenerated requirements/lock.txt, build-tools.txt and dev.txt."
echo "Next: run the test suite, then commit the three files together."
