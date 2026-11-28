"""Shared helpers for scripts/i18n_export.py and scripts/i18n_import.py.

The translations live in the ``TRANSLATIONS`` dict of
``src/utils/translations.py``. These helpers read that dict with ``ast`` (the
app is not imported, so no Qt is needed) and change single values in the
source text, so the rest of the file keeps its exact formatting.
"""

from __future__ import annotations

import ast
import os
import string
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRANSLATIONS_PATH = ROOT / "src" / "utils" / "translations.py"


def checked_csv_path(path: Path) -> Path:
    """
    Resolve a CSV path from the command line and refuse anything else.

    Only a ``.csv`` file inside this repository or the system temp folder
    (used by the tests) is accepted, so a mistyped or crafted argument
    cannot read or overwrite another file.
    """
    resolved = Path(os.path.realpath(path))
    allowed = (Path(os.path.realpath(ROOT)), Path(os.path.realpath(tempfile.gettempdir())))
    if resolved.suffix.lower() != ".csv":
        raise ValueError(f"Not a .csv file: {path}")
    if not any(resolved.is_relative_to(base) for base in allowed):
        raise ValueError(f"The CSV file must be inside the repository: {path}")
    return resolved


LANGUAGES = ("en", "he")


@dataclass(frozen=True)
class Entry:
    """One translation value: its text and where it sits in the source."""

    text: str
    # (line, column, end line, end column); lines start at 1, columns count
    # UTF-8 bytes, as ``ast`` does
    span: tuple[int, int, int, int]


def _translations_node(tree: ast.Module) -> ast.Dict:
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else [getattr(node, "target", None)]
        if any(isinstance(t, ast.Name) and t.id == "TRANSLATIONS" for t in targets) and isinstance(
            node.value, ast.Dict
        ):
            return node.value
    raise ValueError("TRANSLATIONS dict not found")


def read_translations(path: Path = TRANSLATIONS_PATH) -> dict[str, dict[str, Entry]]:
    """Return ``{language: {key: Entry}}`` for every string value in the dict."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result: dict[str, dict[str, Entry]] = {}
    node = _translations_node(tree)
    for lang_key, lang_value in zip(node.keys, node.values, strict=True):
        if not (isinstance(lang_key, ast.Constant) and isinstance(lang_value, ast.Dict)):
            continue
        entries: dict[str, Entry] = {}
        for key, value in zip(lang_value.keys, lang_value.values, strict=True):
            if isinstance(key, ast.Constant) and isinstance(value, ast.Constant) and isinstance(value.value, str):
                span = (value.lineno, value.col_offset, value.end_lineno, value.end_col_offset)
                entries[key.value] = Entry(value.value, span)
        result[lang_key.value] = entries
    return result


def python_literal(text: str) -> str:
    """A double-quoted Python string literal for ``text``.

    Control and invisible format characters (such as U+200F) are written as
    escapes, never as raw characters.
    """
    out = ['"']
    for char in text:
        if char == "\\":
            out.append("\\\\")
        elif char == '"':
            out.append('\\"')
        elif char == "\n":
            out.append("\\n")
        elif char == "\t":
            out.append("\\t")
        elif unicodedata.category(char) in {"Cc", "Cf", "Zl", "Zp"}:
            out.append(f"\\u{ord(char):04x}")
        else:
            out.append(char)
    out.append('"')
    return "".join(out)


def apply_edits(path: Path, edits: list[tuple[tuple[int, int, int, int], str]]) -> None:
    """Replace the source ranges in ``edits`` by new text. Other bytes stay as they are."""
    lines = path.read_bytes().splitlines(keepends=True)
    # Edit from the end of the file, so earlier positions stay valid.
    for (line, col, end_line, end_col), new_text in sorted(edits, reverse=True):
        head = lines[line - 1][:col]
        tail = lines[end_line - 1][end_col:]
        lines[line - 1 : end_line] = [head + new_text.encode("utf-8") + tail]
    path.write_bytes(b"".join(lines))


def placeholders(text: str, key: str = "") -> set[str]:
    """The ``{name}`` fields of a text. A singular text (``*_one``) may leave out ``count``."""
    fields = {name for _, name, _, _ in string.Formatter().parse(text) if name}
    if key.endswith("_one"):
        fields.discard("count")
    return fields
