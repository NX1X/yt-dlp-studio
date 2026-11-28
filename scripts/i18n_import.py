"""Import an edited translations CSV back into src/utils/translations.py.

Only the Hebrew ("he") values change. The English values change only with
--update-en. The script keeps the key order and the formatting of the file and
rewrites just the changed values.

The script refuses the whole file, and changes nothing, when:
  * a key is not in translations.py (add new keys in the code first),
  * a key appears twice, or the columns are not key, en, he,
  * a changed text has other {placeholders} than the English text.

Usage:
    python scripts/i18n_import.py                 # reads translations.csv
    python scripts/i18n_import.py --csv my.csv
    python scripts/i18n_import.py --dry-run       # show what would change
    python scripts/i18n_import.py --update-en     # also apply the "en" column
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _i18n_tools import (
    ROOT,
    TRANSLATIONS_PATH,
    apply_edits,
    placeholders,
    python_literal,
    read_translations,
)  # noqa: E402


class ImportProblem(Exception):
    """The CSV cannot be imported. Nothing was changed."""


def read_csv(path: Path) -> dict[str, dict[str, str]]:
    """Rows as ``{key: {"en": ..., "he": ...}}``. Line breaks are stored as \\n."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = {"key", "en", "he"} - set(reader.fieldnames or [])
        if missing:
            raise ImportProblem(f"The CSV has no column {', '.join(sorted(missing))}. Expected: key, en, he, status.")
        rows: dict[str, dict[str, str]] = {}
        for line, row in enumerate(reader, start=2):
            key = (row["key"] or "").strip()
            if not key:
                continue
            if key in rows:
                raise ImportProblem(f"Line {line}: the key '{key}' appears twice.")
            # A spreadsheet can turn \n into \r\n.
            rows[key] = {lang: (row[lang] or "").replace("\r\n", "\n").replace("\r", "\n") for lang in ("en", "he")}
    return rows


def plan_changes(
    csv_path: Path, translations_path: Path = TRANSLATIONS_PATH, update_en: bool = False
) -> list[tuple[str, str, tuple[int, int, int, int], str]]:
    """List ``(language, key, span, new text)`` for every changed value.

    Raises:
        ImportProblem: for an unknown key, a bad column set or a placeholder mismatch
    """
    rows = read_csv(csv_path)
    data = read_translations(translations_path)
    unknown = sorted(key for key in rows if key not in data["en"])
    if unknown:
        raise ImportProblem(
            "Unknown keys (not in translations.py): " + ", ".join(unknown) + ". Add a new key in the code first."
        )

    languages = ["he"] + (["en"] if update_en else [])
    changes = []
    problems = []
    for key, row in rows.items():
        for lang in languages:
            current = data[lang].get(key)
            new_text = row[lang]
            if current is None or new_text == current.text:
                continue
            if lang == "he" and not new_text.strip():
                problems.append(f"{key}: the Hebrew text is empty")
                continue
            reference = row["en"] if update_en else data["en"][key].text
            if placeholders(new_text, key) != placeholders(reference, key):
                problems.append(
                    f"{key}: {lang} has the fields {sorted(placeholders(new_text, key))}, "
                    f"expected {sorted(placeholders(reference, key))}"
                )
                continue
            changes.append((lang, key, current.span, new_text))
    if problems:
        raise ImportProblem("Cannot import:\n  " + "\n  ".join(problems))
    return changes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n", maxsplit=1)[0])
    parser.add_argument("--csv", type=Path, default=ROOT / "translations.csv", help="edited CSV file")
    parser.add_argument("--translations", type=Path, default=TRANSLATIONS_PATH, help="translations.py to change")
    parser.add_argument("--update-en", action="store_true", help="also apply changes of the en column")
    parser.add_argument("--dry-run", action="store_true", help="show the changes but do not write")
    args = parser.parse_args(argv)

    try:
        changes = plan_changes(args.csv, args.translations, args.update_en)
    except ImportProblem as error:
        print(error, file=sys.stderr)
        return 1

    for lang, key, _span, new_text in changes:
        print(f"{lang} {key}: {new_text[:70]!r}")
    if not changes:
        print("No changes.")
        return 0
    if args.dry_run:
        print(f"{len(changes)} change(s). Dry run, nothing written.")
        return 0
    apply_edits(args.translations, [(span, python_literal(text)) for _lang, _key, span, text in changes])
    print(f"Changed {len(changes)} value(s) in {args.translations}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
