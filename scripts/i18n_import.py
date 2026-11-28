"""Import an edited translations CSV back into src/utils/translations.py.

Only the values of the language in --lang change (default: he). The English
values change only with --update-en. The script keeps the key order and the
formatting of the file and rewrites just the changed values.

With --new, the script adds a language that is not in the file yet. It writes
a block with every key (an empty cell gets the English text, which the app
uses as a fallback until someone translates it) and, for a code that
LANGUAGE_INFO does not list, a line with --native-name and --english-name
(add --rtl for a right-to-left language).

The script refuses the whole file, and changes nothing, when:
  * a key is not in translations.py (add new keys in the code first),
  * a key appears twice, or the columns are not key, en and the language,
  * a changed text has other {placeholders} than the English text,
  * a changed Hebrew or other text is empty.

Usage:
    python scripts/i18n_import.py                      # Hebrew, reads translations.csv
    python scripts/i18n_import.py --lang es --csv es.csv
    python scripts/i18n_import.py --lang es --csv es.csv --new
    python scripts/i18n_import.py --lang xx --new --native-name "Xxx" --english-name "Xxx"
    python scripts/i18n_import.py --dry-run            # show what would change
    python scripts/i18n_import.py --update-en          # also apply the "en" column

The language column may also be called "translation" (the template file).
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _i18n_tools import (  # noqa: E402
    ROOT,
    TRANSLATIONS_PATH,
    apply_edits,
    checked_csv_path,
    dict_end_line,
    insert_lines,
    placeholders,
    python_literal,
    read_language_info,
    read_translations,
)

TEMPLATE_COLUMN = "translation"
LANGUAGE_CODE = re.compile(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})?$")


class ImportProblem(Exception):
    """The CSV cannot be imported. Nothing was changed."""


def read_csv(path: Path, lang: str = "he") -> dict[str, dict[str, str]]:
    """Rows as ``{key: {"en": ..., "text": ...}}``. Line breaks are stored as \\n."""
    with checked_csv_path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        column = lang if lang in fields else TEMPLATE_COLUMN
        missing = {"key", "en", column} - fields
        if missing:
            raise ImportProblem(
                f"The CSV has no column {', '.join(sorted(missing))}. Expected: key, en, {lang}, status."
            )
        rows: dict[str, dict[str, str]] = {}
        for line, row in enumerate(reader, start=2):
            key = (row["key"] or "").strip()
            if not key:
                continue
            if key in rows:
                raise ImportProblem(f"Line {line}: the key '{key}' appears twice.")
            # A spreadsheet can turn \n into \r\n.
            rows[key] = {
                name: (row[column if name == "text" else "en"] or "").replace("\r\n", "\n").replace("\r", "\n")
                for name in ("en", "text")
            }
    return rows


def _check_keys(rows: dict[str, dict[str, str]], data: dict) -> None:
    unknown = sorted(key for key in rows if key not in data["en"])
    if unknown:
        raise ImportProblem(
            "Unknown keys (not in translations.py): " + ", ".join(unknown) + ". Add a new key in the code first."
        )


def plan_changes(
    csv_path: Path, translations_path: Path = TRANSLATIONS_PATH, lang: str = "he", update_en: bool = False
) -> list[tuple[str, str, tuple[int, int, int, int], str]]:
    """List ``(language, key, span, new text)`` for every changed value.

    Raises:
        ImportProblem: for an unknown key or language, a bad column set or a placeholder mismatch
    """
    if lang == "en":
        raise ImportProblem("English is the source language. Use --update-en to change it.")
    rows = read_csv(csv_path, lang)
    data = read_translations(translations_path)
    if lang not in data:
        raise ImportProblem(f"The language '{lang}' is not in translations.py. Add --new to create it.")
    _check_keys(rows, data)

    languages = [lang] + (["en"] if update_en else [])
    changes = []
    problems = []
    for key, row in rows.items():
        for code in languages:
            current = data[code].get(key)
            new_text = row["en"] if code == "en" else row["text"]
            if current is None or new_text == current.text:
                continue
            if not new_text.strip():
                problems.append(f"{key}: the {code} text is empty")
                continue
            reference = row["en"] if update_en else data["en"][key].text
            if placeholders(new_text, key) != placeholders(reference, key):
                problems.append(
                    f"{key}: {code} has the fields {sorted(placeholders(new_text, key))}, "
                    f"expected {sorted(placeholders(reference, key))}"
                )
                continue
            changes.append((code, key, current.span, new_text))
    if problems:
        raise ImportProblem("Cannot import:\n  " + "\n  ".join(problems))
    return changes


def plan_new_language(
    csv_path: Path,
    translations_path: Path,
    lang: str,
    native_name: str = "",
    english_name: str = "",
    rtl: bool = False,
) -> tuple[list[str], str | None]:
    """Source lines for a new language block, and the LANGUAGE_INFO line it needs (or None).

    Raises:
        ImportProblem: for a bad code, a language that exists, an unknown key,
            a placeholder mismatch or missing names for a code that is not listed
    """
    if not LANGUAGE_CODE.match(lang) or lang == "en":
        raise ImportProblem(f"'{lang}' is not a language code (use letters like es, pt, zh-Hans; not en).")
    data = read_translations(translations_path)
    if lang in data:
        raise ImportProblem(f"The language '{lang}' is already in translations.py. Import without --new.")
    rows = read_csv(csv_path, lang)
    _check_keys(rows, data)

    problems = []
    lines = [f'    "{lang}": {{']
    for key, entry in data["en"].items():
        text = rows.get(key, {}).get("text", "")
        if text.strip():
            if placeholders(text, key) != placeholders(entry.text, key):
                problems.append(
                    f"{key}: has the fields {sorted(placeholders(text, key))}, "
                    f"expected {sorted(placeholders(entry.text, key))}"
                )
                continue
        else:
            text = entry.text  # not translated yet: the English text
        lines.append(f"        {python_literal(key)}: {python_literal(text)},")
    lines.append("    },")
    if problems:
        raise ImportProblem("Cannot import:\n  " + "\n  ".join(problems))

    info_line = None
    if lang not in read_language_info(translations_path):
        if not native_name or not english_name:
            raise ImportProblem(
                f"'{lang}' is not in LANGUAGE_INFO. Add --native-name and --english-name (and --rtl if it is written "
                "right to left)."
            )
        info = f"({python_literal(native_name)}, {python_literal(english_name)}, {rtl})"
        info_line = f'    "{lang}": {info},'
    return lines, info_line


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n", maxsplit=1)[0])
    parser.add_argument("--lang", default="he", help="language code, for example he, es, ar (default: he)")
    parser.add_argument("--csv", type=Path, default=ROOT / "translations.csv", help="edited CSV file")
    parser.add_argument("--translations", type=Path, default=TRANSLATIONS_PATH, help="translations.py to change")
    parser.add_argument("--new", action="store_true", help="add a language that is not in translations.py yet")
    parser.add_argument("--native-name", default="", help="with --new: the language name in that language")
    parser.add_argument("--english-name", default="", help="with --new: the language name in English")
    parser.add_argument("--rtl", action="store_true", help="with --new: the language is written right to left")
    parser.add_argument("--update-en", action="store_true", help="also apply changes of the en column")
    parser.add_argument("--dry-run", action="store_true", help="show the changes but do not write")
    args = parser.parse_args(argv)

    try:
        if args.new:
            return _import_new(args)
        changes = plan_changes(args.csv, args.translations, args.lang, args.update_en)
    except (ImportProblem, ValueError) as error:
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


def _import_new(args: argparse.Namespace) -> int:
    lines, info_line = plan_new_language(
        args.csv, args.translations, args.lang, args.native_name, args.english_name, args.rtl
    )
    keys = len(lines) - 2
    if args.dry_run:
        print(f"Would add the language '{args.lang}' with {keys} keys. Dry run, nothing written.")
        return 0
    # LANGUAGE_INFO is below TRANSLATIONS in the file, so it goes in first.
    if info_line:
        insert_lines(args.translations, dict_end_line(args.translations, "LANGUAGE_INFO"), [info_line])
    insert_lines(args.translations, dict_end_line(args.translations, "TRANSLATIONS"), lines)
    print(f"Added the language '{args.lang}' with {keys} keys to {args.translations}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
