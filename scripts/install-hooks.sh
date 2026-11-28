#!/usr/bin/env bash
# Use the git hooks in scripts/git-hooks for this clone.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
chmod +x scripts/git-hooks/pre-commit scripts/git-hooks/commit-msg
git config core.hooksPath scripts/git-hooks
echo "Git hooks installed (core.hooksPath = scripts/git-hooks)."
echo "To remove them: git config --unset core.hooksPath"
