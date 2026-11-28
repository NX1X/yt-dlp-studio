"""Tests for the plain git hooks in scripts/git-hooks.

The hooks are bash scripts, so the tests skip where bash is not available
(for example on the Windows CI runner). The pre-commit tests also need ruff
and black, which are in the dev dependencies.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / "scripts" / "git-hooks"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(
    BASH is None or sys.platform == "win32", reason="the git hooks need bash and a POSIX shell"
)


def _tool_path() -> str:
    """PATH that finds ruff and black the way the venv of this test run does."""
    bindir = str(Path(sys.executable).parent)
    return bindir + os.pathsep + os.environ.get("PATH", "")


def _run_commit_msg(tmp_path: Path, message: str) -> subprocess.CompletedProcess:
    msg = tmp_path / "COMMIT_EDITMSG"
    msg.write_text(message, encoding="utf-8")
    return subprocess.run(
        [BASH, str(HOOKS / "commit-msg"), str(msg)], capture_output=True, text=True, timeout=30, check=False
    )


@pytest.mark.parametrize(
    "message",
    [
        "feat: add a thing\n",
        "fix(queue): keep the order\n",
        "feat!: drop the old format\n",
        "fix(ui)!: rename a button\n\nBody text.\n",
        "i18n: add Spanish\n",
        "deps: bump ruff\n",
        "release: 0.5.0\n",
        "Merge pull request #1 from NX1X/x\n",
        'Revert "feat: add a thing"\n',
        "# a comment line\nci: pin runners\n",
    ],
)
def test_commit_msg_accepts(tmp_path, message):
    result = _run_commit_msg(tmp_path, message)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "message",
    [
        "add a thing\n",
        "Fix: capital type\n",
        "feat:no space\n",
        "feat: \n",
        "feature: wrong type\n",
        "feat(): empty scope\n",
        "\n",
        "# only a comment\n",
    ],
)
def test_commit_msg_rejects(tmp_path, message):
    result = _run_commit_msg(tmp_path, message)
    assert result.returncode == 1
    assert "Conventional Commits" in result.stderr


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, env=env, timeout=30, check=False)


def _run_pre_commit(repo: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "PATH": _tool_path()}
    env.pop("VIRTUAL_ENV", None)
    return subprocess.run(
        [BASH, str(HOOKS / "pre-commit")], cwd=repo, capture_output=True, text=True, env=env, timeout=60, check=False
    )


@pytest.fixture
def repo(tmp_path):
    if shutil.which("git") is None:
        pytest.skip("git is not available")
    path = tmp_path / "repo"
    path.mkdir()
    assert _git(path, "init", "-q").returncode == 0
    return path


def _need_formatters():
    for name in ("ruff", "black"):
        if shutil.which(name, path=_tool_path()) is None:
            pytest.skip(f"{name} is not installed")


def test_pre_commit_accepts_clean_staged_file(repo):
    _need_formatters()
    (repo / "good.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "good.py")
    result = _run_pre_commit(repo)
    assert result.returncode == 0, result.stdout + result.stderr


def test_pre_commit_rejects_bad_staged_file_and_does_not_rewrite_it(repo):
    _need_formatters()
    bad = "import os,sys\nx=1\n"
    (repo / "bad.py").write_text(bad, encoding="utf-8")
    _git(repo, "add", "bad.py")
    result = _run_pre_commit(repo)
    assert result.returncode == 1
    assert "Fix:" in result.stderr
    assert (repo / "bad.py").read_text(encoding="utf-8") == bad


def test_pre_commit_checks_staged_files_only(repo):
    _need_formatters()
    (repo / "good.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "bad.py").write_text("import os,sys\n", encoding="utf-8")  # not staged
    _git(repo, "add", "good.py")
    assert _run_pre_commit(repo).returncode == 0


def test_pre_commit_flags_missing_newline_and_trailing_whitespace(repo):
    (repo / "a.txt").write_text("no newline", encoding="utf-8")
    (repo / "b.txt").write_text("trailing \n", encoding="utf-8")
    _git(repo, "add", "a.txt", "b.txt")
    result = _run_pre_commit(repo)
    assert result.returncode == 1
    assert "a.txt: no newline" in result.stderr
    assert "b.txt: trailing whitespace" in result.stderr


def test_pre_commit_allows_markdown_line_break_spaces(repo):
    (repo / "a.md").write_text("line one  \nline two\n", encoding="utf-8")
    _git(repo, "add", "a.md")
    assert _run_pre_commit(repo).returncode == 0


def test_pre_commit_refuses_file_over_5_mb(repo):
    (repo / "big.dat").write_bytes(b"\0" * (5 * 1024 * 1024 + 1))
    _git(repo, "add", "big.dat")
    result = _run_pre_commit(repo)
    assert result.returncode == 1
    assert "big.dat" in result.stderr


def test_hooks_are_executable():
    for name in ("pre-commit", "commit-msg"):
        assert os.access(HOOKS / name, os.X_OK), f"{name} must have the exec bit"
    assert os.access(ROOT / "scripts" / "install-hooks.sh", os.X_OK)
