"""Export the translations to a CSV file that Excel or LibreOffice can open.

The file has the columns key, en, he and status. It is UTF-8 with a byte
order mark, so Hebrew shows correctly in a spreadsheet. The status is
"missing" when the Hebrew text is empty or the same as the English text,
and "ok" otherwise. (Names such as "WebM" can be the same in both languages
and stay "missing"; ignore those rows.)

Usage:
    python scripts/i18n_export.py                 # writes translations.csv
    python scripts/i18n_export.py --out my.csv
    python scripts/i18n_export.py --only-missing  # just the rows to translate

Edit the "he" column, then run scripts/i18n_import.py.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _i18n_tools import ROOT, TRANSLATIONS_PATH, read_translations  # noqa: E402

COLUMNS = ("key", "en", "he", "status")


def status_of(en: str, he: str) -> str:
    """Return "missing" if the Hebrew text is empty or equals the English text."""
    return "missing" if not he.strip() or he == en else "ok"


def build_rows(translations_path: Path = TRANSLATIONS_PATH, only_missing: bool = False) -> list[list[str]]:
    """Rows in the order of the English dictionary."""
    data = read_translations(translations_path)
    english, hebrew = data["en"], data.get("he", {})
    rows = []
    for key, entry in english.items():
        he = hebrew[key].text if key in hebrew else ""
        status = status_of(entry.text, he)
        if only_missing and status != "missing":
            continue
        rows.append([key, entry.text, he, status])
    return rows


def write_csv(rows: list[list[str]], out: Path) -> None:
    # utf-8-sig writes the byte order mark that spreadsheets need for Hebrew.
    with out.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(COLUMNS)
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n", maxsplit=1)[0])
    parser.add_argument("--out", type=Path, default=ROOT / "translations.csv", help="CSV file to write")
    parser.add_argument("--translations", type=Path, default=TRANSLATIONS_PATH, help="translations.py to read")
    parser.add_argument("--only-missing", action="store_true", help="only rows with status 'missing'")
    args = parser.parse_args(argv)

    rows = build_rows(args.translations, args.only_missing)
    write_csv(rows, args.out)
    missing = sum(1 for row in rows if row[3] == "missing")
    print(f"Wrote {len(rows)} rows to {args.out} ({missing} with status 'missing').")
    return 0


if __name__ == "__main__":
    sys.exit(main())
