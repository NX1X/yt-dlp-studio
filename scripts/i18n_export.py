"""Export the translations of one language to a CSV file for Excel or LibreOffice.

The file has the columns key, en, <language code> and status. It is UTF-8
with a byte order mark, so non-English text shows correctly in a spreadsheet.
The status is "missing" when the translated text is empty or the same as the
English text, and "ok" otherwise. (Names such as "WebM" can be the same in
both languages and stay "missing"; ignore those rows.)

A language that is not in src/utils/translations.py yet exports an empty
column, ready to translate (see docs/TRANSLATING.md).

Usage:
    python scripts/i18n_export.py                 # Hebrew, writes translations.csv
    python scripts/i18n_export.py --lang es       # Spanish (empty if new)
    python scripts/i18n_export.py --out my.csv
    python scripts/i18n_export.py --only-missing  # just the rows to translate
    python scripts/i18n_export.py --repo-files    # refresh translations/*.csv

Edit the language column, then run scripts/i18n_import.py with the same --lang.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _i18n_tools import ROOT, TRANSLATIONS_PATH, checked_csv_path, read_translations  # noqa: E402

REPO_CSV_DIR = ROOT / "translations"
TEMPLATE_NAME = "template.csv"
# Column title of the empty template, for a language that is not in the app yet
TEMPLATE_COLUMN = "translation"


def status_of(en: str, text: str) -> str:
    """Return "missing" if the translated text is empty or equals the English text."""
    return "missing" if not text.strip() or text == en else "ok"


def columns_for(lang: str) -> tuple[str, str, str, str]:
    return ("key", "en", lang, "status")


def build_rows(
    translations_path: Path = TRANSLATIONS_PATH, lang: str = "he", only_missing: bool = False
) -> list[list[str]]:
    """Rows in the order of the English dictionary. A language that does not exist yet is empty."""
    data = read_translations(translations_path)
    english, target = data["en"], data.get(lang, {})
    rows = []
    for key, entry in english.items():
        text = target[key].text if key in target else ""
        status = status_of(entry.text, text)
        if only_missing and status != "missing":
            continue
        rows.append([key, entry.text, text, status])
    return rows


def write_csv(rows: list[list[str]], out: Path, lang: str = "he") -> None:
    # utf-8-sig writes the byte order mark that spreadsheets need for non-English text.
    with checked_csv_path(out).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns_for(lang))
        writer.writerows(rows)


def write_repo_files(translations_path: Path = TRANSLATIONS_PATH, out_dir: Path = REPO_CSV_DIR) -> list[Path]:
    """Write translations/<lang>.csv for every language except English, and translations/template.csv."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for lang in read_translations(translations_path):
        if lang == "en":
            continue
        target = out_dir / f"{lang}.csv"
        write_csv(build_rows(translations_path, lang), target, lang)
        written.append(target)
    template = out_dir / TEMPLATE_NAME
    write_csv(build_rows(translations_path, TEMPLATE_COLUMN), template, TEMPLATE_COLUMN)
    written.append(template)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n", maxsplit=1)[0])
    parser.add_argument("--lang", default="he", help="language code, for example he, es, fr (default: he)")
    parser.add_argument("--out", type=Path, default=None, help="CSV file to write (default: translations.csv)")
    parser.add_argument("--translations", type=Path, default=TRANSLATIONS_PATH, help="translations.py to read")
    parser.add_argument("--only-missing", action="store_true", help="only rows with status 'missing'")
    parser.add_argument("--repo-files", action="store_true", help="write translations/<lang>.csv and template.csv")
    args = parser.parse_args(argv)

    try:
        if args.repo_files:
            for path in write_repo_files(args.translations):
                print(f"Wrote {path}")
            return 0
        if args.lang == "en":
            print("English is the source language. Use --update-en when you import.", file=sys.stderr)
            return 1
        out = args.out or ROOT / "translations.csv"
        rows = build_rows(args.translations, args.lang, args.only_missing)
        write_csv(rows, out, args.lang)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    missing = sum(1 for row in rows if row[3] == "missing")
    print(f"Wrote {len(rows)} rows to {out} ({missing} with status 'missing').")
    return 0


if __name__ == "__main__":
    sys.exit(main())
