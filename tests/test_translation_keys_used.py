"""Every translation key used in src/ must exist in English and Hebrew.

A missing key is shown to the user as the raw key ("button_clear"), so this
test reads every ``tr("...")`` and ``tr_count("...")`` call with a literal key in src/ and checks
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
            if not (
                isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("tr", "tr_count")
            ):
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


@pytest.mark.parametrize("language", ["en", "he"])
def test_keys_built_at_run_time_exist(language):
    """Keys that the code builds from a name (a category, a language code)."""
    from src.utils.constants import (
        AUDIO_FORMAT_LABEL_KEYS,
        AUDIO_FORMATS,
        VIDEO_CONTAINER_FORMATS,
        VIDEO_CONTAINER_LABEL_KEYS,
    )
    from src.utils.error_handler import ErrorCategory

    expected = set()
    for category in ErrorCategory:
        expected |= {f"errcat_{category.value}_{part}" for part in ("title", "message", "suggestions")}
    assert set(VIDEO_CONTAINER_FORMATS) == set(VIDEO_CONTAINER_LABEL_KEYS)
    assert set(AUDIO_FORMATS) == set(AUDIO_FORMAT_LABEL_KEYS)
    expected |= set(VIDEO_CONTAINER_LABEL_KEYS.values()) | set(AUDIO_FORMAT_LABEL_KEYS.values())
    expected |= {key for key in TRANSLATIONS["en"] if key.startswith(("quality_desc_", "language_name_", "log_level_"))}
    missing = sorted(key for key in expected if not TRANSLATIONS[language].get(key))
    assert not missing, f"Keys missing or empty in '{language}': {missing}"


def test_singular_texts_exist_in_both_languages():
    """A ``<key>_one`` text for a number must exist in English and Hebrew, next to ``<key>``."""
    for key in TRANSLATIONS["en"]:
        if key.endswith("_one"):
            assert key in TRANSLATIONS["he"], f"{key} missing in he"
            assert key[: -len("_one")] in TRANSLATIONS["en"], f"{key} has no plain key"
