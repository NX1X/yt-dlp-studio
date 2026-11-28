"""Every translation key used in src/ must exist in English and Hebrew.

A missing key is shown to the user as the raw key ("button_clear"), so this
test reads every ``tr("...")`` call with a literal key in src/ and checks
both dictionaries.
"""

import ast
from pathlib import Path

import pytest

from src.utils.translations import TRANSLATIONS

SRC = Path(__file__).resolve().parent.parent / "src"


def _used_keys() -> dict[str, list[str]]:
    """Map each literal tr() key in src/ to the places that use it."""
    used: dict[str, list[str]] = {}
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "tr"):
                continue
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                used.setdefault(node.args[0].value, []).append(f"{path.relative_to(SRC.parent)}:{node.lineno}")
    return used


USED_KEYS = _used_keys()


def test_finds_tr_calls():
    # Guards the parser itself: the app has hundreds of tr() calls.
    assert len(USED_KEYS) > 100


@pytest.mark.parametrize("language", ["en", "he"])
def test_every_used_key_exists(language):
    missing = {key: places for key, places in USED_KEYS.items() if key not in TRANSLATIONS[language]}
    assert not missing, f"Keys missing in '{language}': {missing}"
