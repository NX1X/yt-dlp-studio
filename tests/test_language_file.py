"""Tests for the saved language choice and its move into the app data folder.

Up to 0.4.0 the language was saved in ~/.yt-dlp-studio/language.json, outside
the app data folder, so the uninstaller purge missed it. It now lives in the
app data folder; an old file is moved there once.
"""

import json
from pathlib import Path

import pytest

import src.utils.translations as tr_module
from src.utils.translations import (
    TranslationManager,
    get_language_file,
    load_saved_language,
    migrate_legacy_language_file,
    save_language,
)


@pytest.fixture
def app_data(tmp_path, monkeypatch):
    """Point the app data folder at tmp_path/appdata."""
    folder = tmp_path / "appdata"
    folder.mkdir()
    monkeypatch.setattr(tr_module, "APP_DATA_DIR", folder)
    return folder


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Point the home folder at tmp_path/home."""
    folder = tmp_path / "home"
    folder.mkdir()
    monkeypatch.setattr(Path, "home", lambda: folder)
    return folder


def _write_legacy(home: Path, content: str) -> Path:
    legacy_dir = home / ".yt-dlp-studio"
    legacy_dir.mkdir()
    legacy_file = legacy_dir / "language.json"
    legacy_file.write_text(content, encoding="utf-8")
    return legacy_file


def test_language_file_is_in_app_data_folder(app_data):
    assert get_language_file() == app_data / "language.json"


def test_save_and_load(app_data, home):
    assert save_language("he") is True
    assert json.loads((app_data / "language.json").read_text(encoding="utf-8")) == {"version": 1, "language": "he"}
    assert load_saved_language() == "he"


def test_save_never_writes_to_the_old_folder(app_data, home):
    save_language("he")
    assert not (home / ".yt-dlp-studio").exists()


def test_nothing_saved_returns_none(app_data, home):
    assert load_saved_language() is None
    assert not (app_data / "language.json").exists()


def test_old_file_is_moved(app_data, home):
    legacy_file = _write_legacy(home, json.dumps({"language": "he"}))

    assert load_saved_language() == "he"

    assert json.loads((app_data / "language.json").read_text(encoding="utf-8")) == {"version": 1, "language": "he"}
    assert not legacy_file.exists()
    assert not legacy_file.parent.exists()


def test_old_folder_with_other_files_is_kept(app_data, home):
    legacy_file = _write_legacy(home, json.dumps({"language": "he"}))
    other = legacy_file.parent / "notes.txt"
    other.write_text("keep me", encoding="utf-8")

    migrate_legacy_language_file()

    assert not legacy_file.exists()
    assert other.read_text(encoding="utf-8") == "keep me"


def test_new_file_wins_over_old_file(app_data, home):
    save_language("en")
    legacy_file = _write_legacy(home, json.dumps({"language": "he"}))

    assert load_saved_language() == "en"
    assert not legacy_file.exists()


@pytest.mark.parametrize("content", ["not json", json.dumps({"language": "xx"}), json.dumps(["he"])])
def test_invalid_old_file_is_deleted_and_ignored(app_data, home, content):
    legacy_file = _write_legacy(home, content)

    assert load_saved_language() is None

    assert not legacy_file.exists()
    assert not (app_data / "language.json").exists()


def test_old_file_kept_when_new_file_cannot_be_written(tmp_path, home, monkeypatch):
    # A regular file where the app data folder should be: mkdir fails.
    blocker = tmp_path / "appdata"
    blocker.write_text("", encoding="utf-8")
    monkeypatch.setattr(tr_module, "APP_DATA_DIR", blocker / "inner")
    legacy_file = _write_legacy(home, json.dumps({"language": "he"}))

    migrate_legacy_language_file()

    assert legacy_file.exists()


def test_migration_runs_once(app_data, home):
    _write_legacy(home, json.dumps({"language": "he"}))
    migrate_legacy_language_file()
    # Nothing left to move; a second run changes nothing.
    migrate_legacy_language_file()
    assert load_saved_language() == "he"


def test_translation_manager_uses_moved_file(app_data, home):
    _write_legacy(home, json.dumps({"language": "he"}))
    assert TranslationManager().get_language() == "he"
