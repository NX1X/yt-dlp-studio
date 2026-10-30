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
#   - Security fixes do not wait for the cooldown. Every package in
#     security_fixes is upgraded (uv otherwise keeps the pins already in the
#     output file). An entry with "=cutoff" also lets that package through
#     up to a cutoff just after its patched release, and no further, so newer
#     unreviewed releases of the same package still wait. Remove an entry
#     once the locks hold the fix and the global cutoff has passed its date.
#   - Order: lock.txt first, then the files constrained by it.
#   - ci-tools.txt is not constrained by lock.txt and targets Python 3.11,
#     which every CI tooling job uses (see requirements/ci-tools.in).
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

# "package" (fix already past the cooldown) or "package=cutoff" (cutoff
# just after the patched release's PyPI upload time).
security_fixes=(
  # certifi 2026.10.18: GHSA-6q48-6c7w-9gw2 (critical, emSign root CAs).
  certifi=2026-10-19T00:00:00Z
  # filelock 4.2.1: GHSA-v4x8-3wr5-3wq8 and 9 more (CI tools only).
  filelock=2026-10-18T00:00:00Z
  # setuptools 84.1.0: GHSA-xmj3-9gf7-h52w (build tools only). 84.2.0
  # followed 27 minutes later, so the cutoff sits between the two.
  setuptools=2026-10-19T20:20:00Z
  # virtualenv 21.14.10: 11 CVEs found by pip-audit (dev tools only); 10 are
  # fixed in 21.14.9, the last in 21.14.10.
  virtualenv=2026-10-18T00:00:00Z
  # urllib3 2.8.0: GHSA-vxq7-64xx-v4gw, GHSA-8988-9cw3-xx77 and 1 more.
  urllib3
  # msgpack 1.2.3: GHSA-j586-36cw-2gc2 (CI tools only).
  msgpack
  # black 26.10.1: GHSA-cg8m-r9f2-5wm2 (CI tools only).
  black
)
exceptions=()
for fix in "${security_fixes[@]}"; do
  exceptions+=(--upgrade-package "${fix%%=*}")
  if [[ $fix == *=* ]]; then
    exceptions+=(--exclude-newer-package "$fix")
  fi
done

base=(--universal --generate-hashes --exclude-newer "$cutoff" "${exceptions[@]}" --quiet)
common=("${base[@]}" --python-version 3.10)

echo "Cooldown cutoff: $cutoff (security exceptions: ${security_fixes[*]})"
uv pip compile pyproject.toml "${common[@]}" -o requirements/lock.txt
uv pip compile requirements/build-tools.in -c requirements/lock.txt "${common[@]}" -o requirements/build-tools.txt
uv pip compile pyproject.toml --extra dev -c requirements/lock.txt "${common[@]}" -o requirements/dev.txt
uv pip compile requirements/ci-tools.in "${base[@]}" --python-version 3.11 -o requirements/ci-tools.txt

echo "Regenerated requirements/lock.txt, build-tools.txt, dev.txt and ci-tools.txt."
echo "Next: run the test suite, then commit the four files together."
