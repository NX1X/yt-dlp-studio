"""Round trip of scripts/i18n_export.py and scripts/i18n_import.py.

The tests work on a copy of src/utils/translations.py in a temporary folder,
so the real file is never changed.
"""

import csv
import difflib
import importlib
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
i18n_export = importlib.import_module("i18n_export")
i18n_import = importlib.import_module("i18n_import")
tools = importlib.import_module("_i18n_tools")


@pytest.fixture
def copy(tmp_path):
    target = tmp_path / "translations.py"
    shutil.copy(ROOT / "src" / "utils" / "translations.py", target)
    return target


@pytest.fixture
def exported(tmp_path, copy):
    out = tmp_path / "translations.csv"
    assert i18n_export.main(["--out", str(out), "--translations", str(copy)]) == 0
    return out


def read_rows(path: Path) -> list[list[str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.reader(handle))


def write_rows(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        csv.writer(handle).writerows(rows)


def set_cell(path: Path, key: str, column: str, value: str) -> None:
    rows = read_rows(path)
    index = rows[0].index(column)
    for row in rows[1:]:
        if row[0] == key:
            row[index] = value
            break
    else:  # pragma: no cover - a test bug
        raise AssertionError(key)
    write_rows(path, rows)


def values(path: Path) -> dict[str, dict[str, str]]:
    return {lang: {k: e.text for k, e in entries.items()} for lang, entries in tools.read_translations(path).items()}


def changed_lines(before: str, after: str) -> list[str]:
    return [
        line
        for line in difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm="", n=0)
        if line[:1] in "+-" and line[:3] not in ("+++", "---")
    ]


class TestExport:
    def test_file_has_a_byte_order_mark_and_the_columns(self, exported):
        assert exported.read_bytes().startswith(b"\xef\xbb\xbf")
        assert read_rows(exported)[0] == ["key", "en", "he", "status"]

    def test_every_key_is_exported_once_in_order(self, exported, copy):
        keys = [row[0] for row in read_rows(exported)[1:]]
        assert keys == list(tools.read_translations(copy)["en"])
        assert len(keys) == len(set(keys))

    def test_status_is_missing_when_he_is_empty_or_equals_en(self, tmp_path):
        assert i18n_export.status_of("Hello", "") == "missing"
        assert i18n_export.status_of("Hello", "  ") == "missing"
        assert i18n_export.status_of("WebM", "WebM") == "missing"
        assert i18n_export.status_of("Hello", "שלום") == "ok"

    def test_only_missing_filters_the_rows(self, tmp_path, copy):
        out = tmp_path / "missing.csv"
        i18n_export.main(["--out", str(out), "--translations", str(copy), "--only-missing"])
        rows = read_rows(out)[1:]
        assert rows and all(row[3] == "missing" for row in rows)

    def test_text_with_line_breaks_and_quotes_survives(self, exported, copy):
        data = values(copy)
        rows = {row[0]: row for row in read_rows(exported)[1:]}
        for key in ("duplicate_download_message", "msg_download_failed_retry"):
            assert rows[key][1] == data["en"][key]
            assert rows[key][2] == data["he"][key]


class TestRoundTrip:
    def test_edit_one_hebrew_value_changes_only_that_value(self, exported, copy):
        before_text = copy.read_text(encoding="utf-8")
        before = values(copy)
        set_cell(exported, "tab_download", "he", "הורדות")
        assert i18n_import.main(["--csv", str(exported), "--translations", str(copy)]) == 0

        after = values(copy)
        assert after["he"]["tab_download"] == "הורדות"
        after["he"]["tab_download"] = before["he"]["tab_download"]
        assert after == before  # nothing else changed
        diff = changed_lines(before_text, copy.read_text(encoding="utf-8"))
        assert len(diff) == 2  # one line out, one line in
        assert '"tab_download": "הורדות"' in diff[1]

    def test_unchanged_csv_leaves_the_file_byte_for_byte(self, exported, copy):
        before = copy.read_bytes()
        assert i18n_import.main(["--csv", str(exported), "--translations", str(copy)]) == 0
        assert copy.read_bytes() == before

    def test_a_multiline_implicit_concatenation_is_replaced_whole(self, exported, copy):
        key = next(
            k
            for k, e in tools.read_translations(copy)["he"].items()
            if e.span[0] != e.span[2]  # value spans several source lines
        )
        set_cell(exported, key, "he", "טקסט חדש")
        before = values(copy)
        i18n_import.main(["--csv", str(exported), "--translations", str(copy)])
        after = values(copy)
        assert after["he"][key] == "טקסט חדש"
        after["he"][key] = before["he"][key]
        assert after == before
        compile(copy.read_text(encoding="utf-8"), str(copy), "exec")

    def test_quotes_backslashes_line_breaks_and_bidi_marks_are_escaped(self, exported, copy):
        text = 'שורה "ראשונה"\nשורה \\ שנייה‏'
        set_cell(exported, "tab_queue", "he", text)
        i18n_import.main(["--csv", str(exported), "--translations", str(copy)])
        assert values(copy)["he"]["tab_queue"] == text
        source = copy.read_text(encoding="utf-8")
        assert "‏" not in source  # written as an escape, not as a raw character
        assert "\\u200f" in source

    def test_a_spreadsheet_that_writes_windows_line_breaks_is_fine(self, exported, copy):
        set_cell(exported, "duplicate_download_message", "he", "א\r\nב")
        i18n_import.main(["--csv", str(exported), "--translations", str(copy)])
        assert values(copy)["he"]["duplicate_download_message"] == "א\nב"

    def test_english_changes_need_the_flag(self, exported, copy):
        set_cell(exported, "tab_queue", "en", "The queue")
        i18n_import.main(["--csv", str(exported), "--translations", str(copy)])
        assert values(copy)["en"]["tab_queue"] == "Queue"
        i18n_import.main(["--csv", str(exported), "--translations", str(copy), "--update-en"])
        assert values(copy)["en"]["tab_queue"] == "The queue"

    def test_dry_run_writes_nothing(self, exported, copy, capsys):
        set_cell(exported, "tab_queue", "he", "התור")
        before = copy.read_bytes()
        assert i18n_import.main(["--csv", str(exported), "--translations", str(copy), "--dry-run"]) == 0
        assert copy.read_bytes() == before
        assert "tab_queue" in capsys.readouterr().out


class TestRefusals:
    def run(self, exported, copy):
        before = copy.read_bytes()
        code = i18n_import.main(["--csv", str(exported), "--translations", str(copy)])
        assert copy.read_bytes() == before, "a refused import must not change the file"
        return code

    def test_unknown_key_is_refused(self, exported, copy, capsys):
        rows = read_rows(exported)
        rows.append(["no_such_key", "x", "y", "ok"])
        write_rows(exported, rows)
        assert self.run(exported, copy) == 1
        assert "no_such_key" in capsys.readouterr().err

    def test_one_unknown_key_blocks_the_other_changes_too(self, exported, copy):
        set_cell(exported, "tab_queue", "he", "התור")
        rows = read_rows(exported)
        rows.append(["no_such_key", "x", "y", "ok"])
        write_rows(exported, rows)
        assert self.run(exported, copy) == 1

    def test_duplicate_key_is_refused(self, exported, copy):
        rows = read_rows(exported)
        rows.append(rows[1])
        write_rows(exported, rows)
        assert self.run(exported, copy) == 1

    def test_missing_column_is_refused(self, tmp_path, copy):
        bad = tmp_path / "bad.csv"
        write_rows(bad, [["key", "he"], ["tab_queue", "התור"]])
        assert self.run(bad, copy) == 1

    def test_changed_placeholders_are_refused(self, exported, copy, capsys):
        set_cell(exported, "batch_count", "he", "כתובות: {total}")
        assert self.run(exported, copy) == 1
        assert "batch_count" in capsys.readouterr().err

    def test_an_emptied_hebrew_text_is_refused(self, exported, copy):
        set_cell(exported, "tab_queue", "he", "")
        assert self.run(exported, copy) == 1

    def test_singular_text_may_leave_out_count(self, exported, copy):
        set_cell(exported, "status_cleared_tasks_one", "he", "הורדה אחת הוסרה מהתור (שינוי).")
        assert i18n_import.main(["--csv", str(exported), "--translations", str(copy)]) == 0


def test_the_csv_file_is_ignored_by_git():
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "translations.csv" in ignore
