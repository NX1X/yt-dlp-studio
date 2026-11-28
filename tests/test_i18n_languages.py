"""A new language needs no code change: the import script adds it, the app lists it.

The tests add two fake languages (zz, left to right, and yy, right to left)
to a copy of src/utils/translations.py with scripts/i18n_import.py --new,
then put the result into the running app and check the language list, the
fallback to English, the layout direction and the Qt translator.
"""

import importlib
import shutil
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

import src.backend.history_manager as hm_module
import src.ui.main_window as mw_module
import src.utils.translations as tr_module
from src.backend.config_manager import ConfigManager
from src.utils.translations import TRANSLATIONS, TranslationManager, get_translation_manager, is_rtl_language, tr

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
i18n_export = importlib.import_module("i18n_export")
i18n_import = importlib.import_module("i18n_import")
tools = importlib.import_module("_i18n_tools")


@pytest.fixture
def copy(tmp_path):
    target = tmp_path / "translations.py"
    shutil.copy(ROOT / "src" / "utils" / "translations.py", target)
    return target


def template_with(tmp_path, copy, answers: dict[str, str], column="translation"):
    """Export the empty template, fill some cells, return the CSV path."""
    csv_path = tmp_path / "new.csv"
    i18n_export.write_csv(i18n_export.build_rows(copy, column), csv_path, column)
    rows = tools_rows(csv_path)
    for row in rows[1:]:
        if row[0] in answers:
            row[2] = answers[row[0]]
    write_rows(csv_path, rows)
    return csv_path


def tools_rows(path):
    import csv

    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.reader(handle))


def write_rows(path, rows):
    import csv

    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        csv.writer(handle).writerows(rows)


def add_language(tmp_path, copy, code, answers, *extra):
    csv_path = template_with(tmp_path, copy, answers)
    argv = ["--lang", code, "--csv", str(csv_path), "--translations", str(copy), "--new", *extra]
    assert i18n_import.main(argv) == 0
    return tools.read_translations(copy)[code], tools.read_language_info(copy)


@pytest.fixture
def fake_languages(qapp, tmp_path, copy, monkeypatch):
    """zz (LTR) and yy (RTL) added by the import script and put into the app."""
    zz, _ = add_language(
        tmp_path, copy, "zz", {"tab_download": "Zed download"}, "--native-name", "Zedish", "--english-name", "Zedish"
    )
    yy, info = add_language(
        tmp_path,
        copy,
        "yy",
        {"tab_download": "Why download (yy)"},
        "--native-name",
        "Yyish",
        "--english-name",
        "Yyish",
        "--rtl",
    )
    for code, entries in (("zz", zz), ("yy", yy)):
        monkeypatch.setitem(TRANSLATIONS, code, {k: e.text for k, e in entries.items()})
        monkeypatch.setitem(tr_module.LANGUAGE_INFO, code, info[code])
    # A key that the new language does not have yet falls back to English.
    del TRANSLATIONS["zz"]["tab_queue"]
    yield
    get_translation_manager().set_language("en")
    QApplication.instance().setLayoutDirection(Qt.LeftToRight)


class TestImportNew:
    def test_block_has_every_key_and_english_for_the_untranslated(self, tmp_path, copy):
        block, info = add_language(
            tmp_path,
            copy,
            "zz",
            {"tab_download": "Zed download"},
            "--native-name",
            "Zedish",
            "--english-name",
            "Zedish",
        )
        english = tools.read_translations(copy)["en"]
        assert list(block) == list(english)
        assert block["tab_download"].text == "Zed download"
        assert block["tab_queue"].text == english["tab_queue"].text
        assert info["zz"] == ("Zedish", "Zedish", False)
        compile(copy.read_text(encoding="utf-8"), str(copy), "exec")

    def test_the_rest_of_the_file_is_unchanged(self, tmp_path, copy):
        before = tools.read_translations(copy)
        add_language(tmp_path, copy, "zz", {}, "--native-name", "Zedish", "--english-name", "Zedish")
        after = tools.read_translations(copy)
        assert {k: v for k, v in after.items() if k != "zz"}.keys() == before.keys()
        for lang in before:
            assert {k: e.text for k, e in after[lang].items()} == {k: e.text for k, e in before[lang].items()}

    def test_a_code_in_the_table_needs_no_names(self, tmp_path, copy):
        block, info = add_language(tmp_path, copy, "es", {"tab_download": "Descargar"})
        assert block["tab_download"].text == "Descargar"
        assert info["es"][1] == "Spanish"

    def test_rtl_flag_is_written(self, tmp_path, copy):
        _, info = add_language(tmp_path, copy, "yy", {}, "--native-name", "Y", "--english-name", "Y", "--rtl")
        assert info["yy"][2] is True

    def test_the_exported_file_of_the_new_language_has_its_own_column(self, tmp_path, copy):
        add_language(
            tmp_path, copy, "zz", {"tab_download": "Zed download"}, "--native-name", "Z", "--english-name", "Z"
        )
        out = tmp_path / "zz.csv"
        assert i18n_export.main(["--lang", "zz", "--out", str(out), "--translations", str(copy)]) == 0
        rows = tools_rows(out)
        assert rows[0] == ["key", "en", "zz", "status"]
        assert ["tab_download", "Download", "Zed download", "ok"] in rows

    @pytest.mark.parametrize("code", ["en", "x", "Spanish", "zz;", "../x"])
    def test_bad_code_is_refused(self, tmp_path, copy, code):
        csv_path = template_with(tmp_path, copy, {})
        before = copy.read_bytes()
        argv = [
            "--lang",
            code,
            "--csv",
            str(csv_path),
            "--translations",
            str(copy),
            "--new",
            "--native-name",
            "Z",
            "--english-name",
            "Z",
        ]
        assert i18n_import.main(argv) == 1
        assert copy.read_bytes() == before

    def test_existing_language_with_new_is_refused(self, tmp_path, copy):
        csv_path = template_with(tmp_path, copy, {})
        assert i18n_import.main(["--lang", "he", "--csv", str(csv_path), "--translations", str(copy), "--new"]) == 1

    def test_unknown_language_without_new_is_refused(self, tmp_path, copy):
        csv_path = template_with(tmp_path, copy, {})
        before = copy.read_bytes()
        assert i18n_import.main(["--lang", "es", "--csv", str(csv_path), "--translations", str(copy)]) == 1
        assert copy.read_bytes() == before

    def test_names_are_required_for_a_code_that_is_not_listed(self, tmp_path, copy):
        csv_path = template_with(tmp_path, copy, {})
        before = copy.read_bytes()
        assert i18n_import.main(["--lang", "zz", "--csv", str(csv_path), "--translations", str(copy), "--new"]) == 1
        assert copy.read_bytes() == before

    def test_unknown_key_and_placeholder_mismatch_are_refused(self, tmp_path, copy):
        csv_path = template_with(tmp_path, copy, {"batch_count": "bad {total}"})
        before = copy.read_bytes()
        argv = ["--lang", "es", "--csv", str(csv_path), "--translations", str(copy), "--new"]
        assert i18n_import.main(argv) == 1
        rows = tools_rows(csv_path)
        rows[1:] = [r for r in rows[1:] if r[0] != "batch_count"] + [["no_such_key", "x", "y", "ok"]]
        write_rows(csv_path, rows)
        assert i18n_import.main(argv) == 1
        assert copy.read_bytes() == before

    def test_import_into_an_existing_language_with_lang(self, tmp_path, copy):
        out = tmp_path / "he.csv"
        i18n_export.main(["--lang", "he", "--out", str(out), "--translations", str(copy)])
        rows = tools_rows(out)
        for row in rows[1:]:
            if row[0] == "tab_queue":
                row[2] = "התור"
        write_rows(out, rows)
        assert i18n_import.main(["--lang", "he", "--csv", str(out), "--translations", str(copy)]) == 0
        assert tools.read_translations(copy)["he"]["tab_queue"].text == "התור"


class TestRepoCsvFiles:
    def test_committed_csv_files_match_the_translations(self, tmp_path):
        """translations/*.csv are generated. Run: python scripts/i18n_export.py --repo-files"""
        out = tmp_path / "translations"
        written = i18n_export.write_repo_files(tools.TRANSLATIONS_PATH, out)
        assert {p.name for p in written} == {p.name for p in (ROOT / "translations").glob("*.csv")}
        for path in written:
            committed = (ROOT / "translations" / path.name).read_bytes()
            message = f"translations/{path.name} is out of date: run scripts/i18n_export.py --repo-files"
            assert path.read_bytes() == committed, message


class TestAppUsesTheNewLanguage:
    def test_it_is_in_the_language_list(self, fake_languages):
        languages = TranslationManager().get_available_languages()
        assert list(languages)[:2] == ["en", "he"]
        assert languages["zz"] == "Zedish"
        assert languages["yy"] == "Yyish"

    def test_it_is_in_the_settings_combo(self, fake_languages, qtbot, tmp_path, monkeypatch):
        monkeypatch.setattr(mw_module, "APP_DATA_DIR", tmp_path)
        monkeypatch.setattr(hm_module, "APP_DATA_DIR", tmp_path)
        config = ConfigManager(config_path=tmp_path / "config.json")
        config.load_config()
        window = mw_module.MainWindow(config)
        qtbot.addWidget(window)
        assert window.settings_tab.language_combo.findData("zz") >= 0
        window.notification_manager.hide_tray_icon()

    def test_missing_key_falls_back_to_english(self, fake_languages):
        manager = get_translation_manager()
        manager.set_language("zz")
        assert tr("tab_download") == "Zed download"
        assert tr("tab_queue") == TRANSLATIONS["en"]["tab_queue"]
        assert tr("no_such_key_at_all") == "no_such_key_at_all"

    def test_rtl_follows_the_table(self, fake_languages):
        for code in ("he", "fa", "ur", "yi", "yy"):
            assert is_rtl_language(code), code
        for code in ("en", "es", "zz", "xx"):
            assert not is_rtl_language(code), code
        manager = get_translation_manager()
        manager.set_language("yy")
        assert manager.is_rtl()
        manager.set_language("zz")
        assert not manager.is_rtl()

    def test_rlm_fix_applies_to_every_rtl_language(self, fake_languages):
        manager = get_translation_manager()
        manager.set_language("yy")
        assert tr("tab_download").endswith("‏")  # "...(yy)" gets the right-to-left mark
        manager.set_language("zz")
        assert not tr("tab_download").endswith("‏")

    def test_layout_flips_for_an_rtl_language(self, fake_languages, qtbot, tmp_path, monkeypatch):
        monkeypatch.setattr(mw_module, "APP_DATA_DIR", tmp_path)
        monkeypatch.setattr(hm_module, "APP_DATA_DIR", tmp_path)
        config = ConfigManager(config_path=tmp_path / "config.json")
        config.load_config()
        manager = get_translation_manager()
        manager.set_language("yy")
        window = mw_module.MainWindow(config)
        qtbot.addWidget(window)
        assert QApplication.layoutDirection() == Qt.RightToLeft
        manager.set_language("zz")
        window._apply_rtl_layout()
        assert QApplication.layoutDirection() == Qt.LeftToRight
        window.notification_manager.hide_tray_icon()

    def test_qt_translator_is_loaded_when_the_file_exists(self, qtbot, tmp_path, monkeypatch):
        monkeypatch.setattr(mw_module, "APP_DATA_DIR", tmp_path)
        monkeypatch.setattr(hm_module, "APP_DATA_DIR", tmp_path)
        config = ConfigManager(config_path=tmp_path / "config.json")
        config.load_config()
        window = mw_module.MainWindow(config)
        qtbot.addWidget(window)
        try:
            window._install_qt_translator("fr")  # PySide6 ships qtbase_fr.qm
            assert window._qt_translator is not None
            window._install_qt_translator("zz")  # no qtbase_zz.qm
            assert window._qt_translator is None
        finally:
            window._install_qt_translator("en")
            window.notification_manager.hide_tray_icon()
