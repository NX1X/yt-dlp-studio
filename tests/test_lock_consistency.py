"""The hash-pinned lock files must agree with pyproject.toml.

Renovate bumps version bounds in pyproject.toml without regenerating the
locks. In 2026-09 that left requirements/lock.txt pinning PySide6 6.11.0
while pyproject.toml required >=6.11.2; CI hid it because an unhashed
editable install upgraded past the lock. These tests catch that drift.
Fix a failure with scripts/relock.sh.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parent.parent
PIN_RE = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s\\;]+)", re.MULTILINE)


def _pins(lock_name: str) -> dict[str, str]:
    text = (ROOT / "requirements" / lock_name).read_text(encoding="utf-8")
    return {canonicalize_name(name): version for name, version in PIN_RE.findall(text)}


def _pyproject_list(key_line: str) -> list[Requirement]:
    """Parse one dependency list from pyproject.toml without tomllib (3.11+ only)."""
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    block = text[text.index(key_line) + 1 :]  # +1 skips the leading newline
    block = block[: block.index("\n]")]
    reqs = []
    for line in block.splitlines()[1:]:
        line = line.strip()
        if line and not line.startswith("#"):
            reqs.append(Requirement(line.rstrip(",").strip('"')))
    assert reqs, f"no entries found under {key_line!r}"
    return reqs


RUNTIME = _pyproject_list("\ndependencies = [")
DEV = _pyproject_list("\ndev = [")


@pytest.mark.parametrize("lock_name", ["lock.txt", "dev.txt"])
@pytest.mark.parametrize("req", RUNTIME, ids=lambda r: r.name)
def test_runtime_pins_satisfy_pyproject(lock_name, req):
    pins = _pins(lock_name)
    name = canonicalize_name(req.name)
    assert name in pins, f"{req.name} is missing from requirements/{lock_name}"
    assert req.specifier.contains(pins[name], prereleases=True), (
        f"requirements/{lock_name} pins {req.name}=={pins[name]}, "
        f"but pyproject.toml requires {req.specifier}. Run scripts/relock.sh."
    )


@pytest.mark.parametrize("req", DEV, ids=lambda r: r.name)
def test_dev_pins_satisfy_pyproject(req):
    pins = _pins("dev.txt")
    name = canonicalize_name(req.name)
    assert name in pins, f"{req.name} is missing from requirements/dev.txt"
    assert req.specifier.contains(pins[name], prereleases=True), (
        f"requirements/dev.txt pins {req.name}=={pins[name]}, "
        f"but pyproject.toml requires {req.specifier}. Run scripts/relock.sh."
    )


def test_shared_pins_agree_between_locks():
    """dev.txt and build-tools.txt are constrained by lock.txt; shared pins must match."""
    lock = _pins("lock.txt")
    for other in ("dev.txt", "build-tools.txt"):
        pins = _pins(other)
        mismatched = {n: (lock[n], pins[n]) for n in lock.keys() & pins.keys() if lock[n] != pins[n]}
        assert not mismatched, f"{other} disagrees with lock.txt: {mismatched}"


@pytest.mark.parametrize("lock_name", ["lock.txt", "dev.txt", "build-tools.txt"])
def test_curl_cffi_never_locked(lock_name):
    """curl_cffi is banned by the project's software-origin policy."""
    assert "curl-cffi" not in _pins(lock_name)


def test_pip_lock_matches_dev_lock():
    """CI upgrades pip from requirements/pip.txt; it must be the pip dev.txt pins."""
    pip_pins = _pins("pip.txt")
    assert set(pip_pins) == {"pip"}, f"pip.txt must pin only pip, found {sorted(pip_pins)}"
    assert pip_pins["pip"] == _pins("dev.txt")["pip"]
