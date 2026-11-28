"""
Tests for the versioned app data files and their migrations.

Covers the framework in src/utils/file_formats.py and the files that use it:
the settings (ConfigManager), the download history (HistoryManager) and the
language choice. The queue file has its own tests in test_queue_persistence.py.
Every test uses ``tmp_path``; none touches the real app data folder.
"""

import json
from datetime import datetime
from unittest.mock import patch

import pytest

import src.backend.history_manager as hm_module
import src.utils.translations as tr_module
from src.backend.config_manager import ConfigManager
from src.models.download_history import HistoryEntry
from src.utils.file_formats import (
    CONFIG_FORMAT,
    HISTORY_FORMAT,
    LANGUAGE_FORMAT,
    QUEUE_FORMAT,
    VERSION_KEY,
    FileFormat,
    FileState,
    bad_copy_path,
    load_json_file,
    migrate,
    newer_backup_path,
    read_version,
    save_json_file,
)


def write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return path.read_text(encoding="utf-8")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


# A format with two steps, to check the order of the migrations.
def _add_a(data):
    return {**data, "a": 1}


def _a_to_b(data):
    return {"b": data["a"] + 1, **{k: v for k, v in data.items() if k != "a"}}


TWO_STEPS = FileFormat("test", migrations=(_add_a, _a_to_b))


# ----------------------------------------------------------------------
# Framework
# ----------------------------------------------------------------------


class TestFileFormat:
    def test_current_versions(self):
        assert CONFIG_FORMAT.current_version == 1
        assert HISTORY_FORMAT.current_version == 1
        assert LANGUAGE_FORMAT.current_version == 1
        assert QUEUE_FORMAT.current_version == 1
        assert QUEUE_FORMAT.first_version == 1
        assert TWO_STEPS.current_version == 2

    def test_one_version_key_for_all_files(self):
        assert VERSION_KEY == "version"

    @pytest.mark.parametrize(
        ("data", "expected"),
        [({}, 0), ({"version": 0}, 0), ({"version": 3}, 3), ({"version": -1}, None)],
    )
    def test_read_version(self, data, expected):
        assert read_version(data) == expected

    @pytest.mark.parametrize("value", ["1", 1.0, True, None, [1]])
    def test_read_version_rejects_non_int(self, value):
        assert read_version({"version": value}) is None

    def test_migrations_run_in_order(self):
        assert migrate({"x": 0}, TWO_STEPS, 0) == {"x": 0, "b": 2}
        assert migrate({"a": 5}, TWO_STEPS, 1) == {"b": 6}
        assert migrate({"b": 9}, TWO_STEPS, 2) == {"b": 9}

    @pytest.mark.parametrize("version", [-1, 3])
    def test_migrate_rejects_unknown_version(self, version):
        with pytest.raises(ValueError):
            migrate({}, TWO_STEPS, version)

    def test_migration_must_return_a_dict(self):
        bad = FileFormat("bad", migrations=(lambda data: None,))
        with pytest.raises(ValueError):
            migrate({}, bad, 0)


class TestLoad:
    def test_missing_file(self, tmp_path):
        result = load_json_file(tmp_path / "f.json", TWO_STEPS)
        assert result.state is FileState.MISSING
        assert result.data is None

    def test_current_version_is_read_as_is(self, tmp_path):
        path = tmp_path / "f.json"
        write_json(path, {"version": 2, "b": 1})
        result = load_json_file(path, TWO_STEPS)
        assert result.state is FileState.CURRENT
        assert result.data == {"b": 1}  # no version key in the data
        assert result.file_version == 2

    def test_file_without_version_is_v0_and_migrated_in_memory(self, tmp_path):
        path = tmp_path / "f.json"
        original = write_json(path, {"x": 1})
        result = load_json_file(path, TWO_STEPS)
        assert result.state is FileState.MIGRATED
        assert result.file_version == 0
        assert result.data == {"x": 1, "b": 2}
        assert path.read_text(encoding="utf-8") == original  # written on next save only

    def test_newer_version_returns_data_and_keeps_file(self, tmp_path):
        path = tmp_path / "f.json"
        original = write_json(path, {"version": 5, "b": 1, "future": True})
        result = load_json_file(path, TWO_STEPS)
        assert result.state is FileState.NEWER
        assert result.file_version == 5
        assert result.data == {"b": 1, "future": True}
        assert path.read_text(encoding="utf-8") == original
        assert not newer_backup_path(path, 5).exists()  # only before the first write

    @pytest.mark.parametrize(
        "content",
        ["{not json", "[]", "42", '"text"', '{"version": "1"}', '{"version": -2}', '{"version": true}'],
    )
    def test_damaged_file_is_kept_as_bad(self, tmp_path, content):
        path = tmp_path / "f.json"
        path.write_text(content, encoding="utf-8")
        result = load_json_file(path, TWO_STEPS)
        assert result.state is FileState.DAMAGED
        assert result.data is None
        assert bad_copy_path(path).read_text(encoding="utf-8") == content
        assert bad_copy_path(path).name == "f.json.bad"

    def test_invalid_utf8_is_damaged(self, tmp_path):
        path = tmp_path / "f.json"
        path.write_bytes(b"\xff\xfe\x00garbage")
        assert load_json_file(path, TWO_STEPS).state is FileState.DAMAGED
        assert bad_copy_path(path).read_bytes() == b"\xff\xfe\x00garbage"

    def test_empty_file_is_damaged_without_copy(self, tmp_path):
        path = tmp_path / "f.json"
        path.write_text("  \n", encoding="utf-8")
        assert load_json_file(path, TWO_STEPS).state is FileState.DAMAGED
        assert not bad_copy_path(path).exists()

    def test_unreadable_path_does_not_raise(self, tmp_path):
        path = tmp_path / "f.json"
        path.mkdir()  # reading a folder raises an OSError
        assert load_json_file(path, TWO_STEPS).state is FileState.DAMAGED

    def test_version_below_first_version_is_damaged(self, tmp_path):
        path = tmp_path / "q.json"
        write_json(path, {"tasks": []})  # the queue has no version 0
        assert load_json_file(path, QUEUE_FORMAT).state is FileState.DAMAGED
        assert bad_copy_path(path).exists()

    def test_failed_migration_is_damaged(self, tmp_path):
        path = tmp_path / "f.json"
        write_json(path, {"version": 1})  # _a_to_b needs "a"
        assert load_json_file(path, TWO_STEPS).state is FileState.DAMAGED
        assert bad_copy_path(path).exists()


class TestSave:
    def test_save_writes_current_version_first(self, tmp_path):
        path = tmp_path / "f.json"
        save_json_file(path, TWO_STEPS, {"b": 1, "version": 99})
        text = path.read_text(encoding="utf-8")
        assert json.loads(text) == {"version": 2, "b": 1}
        assert text.lstrip("{\n ").startswith('"version"')

    def test_round_trip(self, tmp_path):
        path = tmp_path / "f.json"
        data = {"b": 3, "name": "שלום", "list": [1, 2]}
        save_json_file(path, TWO_STEPS, data)
        result = load_json_file(path, TWO_STEPS)
        assert result.state is FileState.CURRENT
        assert result.data == data

    def test_migrated_file_is_written_back_on_save(self, tmp_path):
        path = tmp_path / "f.json"
        write_json(path, {"x": 1})
        save_json_file(path, TWO_STEPS, load_json_file(path, TWO_STEPS).data)
        assert read_json(path) == {"version": 2, "x": 1, "b": 2}
        assert load_json_file(path, TWO_STEPS).state is FileState.CURRENT

    def test_newer_file_is_backed_up_before_first_write(self, tmp_path):
        path = tmp_path / "f.json"
        original = write_json(path, {"version": 4, "b": 1, "future": 1})
        backup = tmp_path / "f.json.v4.bak"

        save_json_file(path, TWO_STEPS, {"b": 1})
        assert backup.read_text(encoding="utf-8") == original
        assert read_json(path) == {"version": 2, "b": 1}

        backup.unlink()
        save_json_file(path, TWO_STEPS, {"b": 2})
        assert not backup.exists()  # already at the current version

    def test_failed_backup_does_not_overwrite_newer_file(self, tmp_path):
        path = tmp_path / "f.json"
        original = write_json(path, {"version": 4, "b": 1})
        with patch("src.utils.file_formats.shutil.copyfile", side_effect=OSError("disk full")):
            with pytest.raises(OSError):
                save_json_file(path, TWO_STEPS, {"b": 1})
        assert path.read_text(encoding="utf-8") == original

    def test_damaged_or_missing_file_needs_no_backup(self, tmp_path):
        path = tmp_path / "f.json"
        save_json_file(path, TWO_STEPS, {"b": 1})  # missing
        path.write_text("garbage", encoding="utf-8")
        save_json_file(path, TWO_STEPS, {"b": 1})  # damaged
        assert sorted(p.name for p in tmp_path.iterdir()) == ["f.json"]

    def test_failed_write_keeps_old_file(self, tmp_path):
        path = tmp_path / "f.json"
        save_json_file(path, TWO_STEPS, {"b": 1})
        before = path.read_text(encoding="utf-8")
        with patch("src.utils.file_formats.os.replace", side_effect=OSError("disk full")):
            with pytest.raises(OSError):
                save_json_file(path, TWO_STEPS, {"b": 2})
        assert path.read_text(encoding="utf-8") == before
        assert [p.name for p in tmp_path.iterdir()] == ["f.json"]  # temp file removed


# ----------------------------------------------------------------------
# Settings file
# ----------------------------------------------------------------------

# A settings file as 0.4.x writes it: no version key
CONFIG_V0 = {
    "output_directory": "/home/user/Videos",
    "default_quality": "720p (HD)",
    "window_width": 1000,
    "window_height": 800,
    "last_url": "https://www.youtube.com/watch?v=abc",
    "check_updates_on_startup": True,
    "skipped_update_version": "0.4.0",
    "last_update_check": "2026-11-01T10:00:00+00:00",
    "notifications_enabled": False,
    "close_to_tray": True,
}


class TestConfigFile:
    def test_v0_is_migrated_to_v1(self, tmp_path):
        path = tmp_path / "config.json"
        original = write_json(path, CONFIG_V0)
        manager = ConfigManager(path)
        config = manager.load_config()

        assert config.to_dict() == CONFIG_V0  # every value kept
        assert path.read_text(encoding="utf-8") == original  # not written yet

        assert manager.save_config(config) is True
        assert read_json(path) == {"version": 1, **CONFIG_V0}

    def test_round_trip(self, tmp_path):
        path = tmp_path / "config.json"
        manager = ConfigManager(path)
        manager.load_config()
        manager.update_config(default_quality="1080p (Full HD)", close_to_tray=True)

        assert read_json(path)["version"] == 1
        config = ConfigManager(path).load_config()
        assert config.default_quality == "1080p (Full HD)"
        assert config.close_to_tray is True

    def test_newer_version_loads_known_fields_and_keeps_backup(self, tmp_path, caplog):
        path = tmp_path / "config.json"
        original = write_json(path, {"version": 2, **CONFIG_V0, "proxy": "http://p:8080"})
        manager = ConfigManager(path)
        with caplog.at_level("WARNING"):
            config = manager.load_config()

        assert config.default_quality == "720p (HD)"
        assert "newer than this app" in caplog.text
        assert path.read_text(encoding="utf-8") == original

        manager.update_config(window_width=1200)
        assert (tmp_path / "config.json.v2.bak").read_text(encoding="utf-8") == original
        assert read_json(path)["version"] == 1
        assert read_json(path)["window_width"] == 1200

    def test_damaged_file_is_kept_as_bad_and_defaults_used(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text('{"output_directory": ', encoding="utf-8")
        config = ConfigManager(path).load_config()

        assert config.default_quality == "Best Quality"
        assert (tmp_path / "config.json.bad").read_text(encoding="utf-8") == '{"output_directory": '

    @pytest.mark.parametrize(
        "change",
        [{"window_width": 10}, {"window_width": "wide"}, {"default_quality": "nope"}, {"output_directory": None}],
    )
    def test_invalid_values_are_kept_as_bad_and_defaults_used(self, tmp_path, change):
        path = tmp_path / "config.json"
        write_json(path, {**CONFIG_V0, **change})
        config = ConfigManager(path).load_config()
        assert config.window_width == 900
        assert (tmp_path / "config.json.bad").exists()

    def test_missing_required_field_is_bad(self, tmp_path):
        path = tmp_path / "config.json"
        write_json(path, {"version": 1, "default_quality": "720p (HD)"})
        config = ConfigManager(path).load_config()
        assert config.default_quality == "Best Quality"
        assert (tmp_path / "config.json.bad").exists()


# ----------------------------------------------------------------------
# History file
# ----------------------------------------------------------------------


def history_entry_dict(n=0, **changes):
    entry = HistoryEntry(
        url=f"https://www.youtube.com/watch?v={n}",
        title=f"Video {n}",
        quality="1080p",
        output_directory="/tmp/downloads",
        filename=f"video{n}.mp4",
        status="completed",
        timestamp=datetime(2026, 11, 1, 12, 0, n),
        file_size=1000 + n,
        platform="youtube",
    ).to_dict()
    entry.update(changes)
    return entry


@pytest.fixture
def history_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(hm_module, "APP_DATA_DIR", tmp_path)
    return tmp_path


class TestHistoryFile:
    def test_v0_is_migrated_to_v1(self, history_dir):
        path = history_dir / "download_history.json"
        v0 = {"max_entries": 500, "entries": [history_entry_dict(0), history_entry_dict(1)]}
        original = write_json(path, v0)

        manager = hm_module.HistoryManager()
        assert [e.title for e in manager.history.entries] == ["Video 0", "Video 1"]
        assert manager.history.max_entries == 500
        assert path.read_text(encoding="utf-8") == original  # not written yet

        assert manager.save() is True
        assert read_json(path) == {"version": 1, **v0}

    def test_round_trip(self, history_dir):
        path = history_dir / "download_history.json"
        write_json(path, {"version": 1, "max_entries": 1000, "entries": [history_entry_dict(3)]})
        manager = hm_module.HistoryManager()
        manager.save()

        again = hm_module.HistoryManager()
        assert [e.to_dict() for e in again.history.entries] == [history_entry_dict(3)]
        assert read_json(path)["version"] == 1

    def test_newer_version_loads_known_fields_and_keeps_backup(self, history_dir, caplog):
        path = history_dir / "download_history.json"
        data = {"version": 3, "max_entries": 1000, "tags": [], "entries": [history_entry_dict(0, rating=5)]}
        original = write_json(path, data)
        with caplog.at_level("WARNING"):
            manager = hm_module.HistoryManager()

        assert manager.history.entries[0].title == "Video 0"
        assert "newer than this app" in caplog.text
        assert not (history_dir / "download_history.json.v3.bak").exists()

        manager.save()
        assert (history_dir / "download_history.json.v3.bak").read_text(encoding="utf-8") == original
        assert read_json(path)["version"] == 1

    def test_damaged_file_is_kept_as_bad_and_history_starts_empty(self, history_dir):
        path = history_dir / "download_history.json"
        path.write_text('{"entries": [', encoding="utf-8")
        manager = hm_module.HistoryManager()

        assert manager.history.entries == []
        assert (history_dir / "download_history.json.bad").read_text(encoding="utf-8") == '{"entries": ['

    def test_damaged_file_survives_the_next_save(self, history_dir):
        path = history_dir / "download_history.json"
        path.write_text("garbage", encoding="utf-8")
        manager = hm_module.HistoryManager()
        manager.save()
        assert read_json(path)["version"] == 1
        assert (history_dir / "download_history.json.bad").read_text(encoding="utf-8") == "garbage"

    def test_entries_not_a_list_is_bad(self, history_dir):
        write_json(history_dir / "download_history.json", {"version": 1, "entries": {}})
        manager = hm_module.HistoryManager()
        assert manager.history.entries == []
        assert (history_dir / "download_history.json.bad").exists()

    def test_invalid_entries_are_skipped_and_file_kept_as_bad(self, history_dir):
        entries = [history_entry_dict(0), {"url": "x"}, "nonsense", history_entry_dict(1, timestamp=5)]
        write_json(history_dir / "download_history.json", {"entries": entries})
        manager = hm_module.HistoryManager()
        assert [e.title for e in manager.history.entries] == ["Video 0"]
        assert (history_dir / "download_history.json.bad").exists()

    @pytest.mark.parametrize("value", [0, -5, "10", True, None])
    def test_invalid_max_entries_takes_default(self, history_dir, value):
        write_json(history_dir / "download_history.json", {"max_entries": value, "entries": []})
        assert hm_module.HistoryManager().history.max_entries == 1000


# ----------------------------------------------------------------------
# Language file
# ----------------------------------------------------------------------


@pytest.fixture
def language_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(tr_module, "APP_DATA_DIR", tmp_path)
    return tmp_path


class TestLanguageFile:
    def test_v0_is_read(self, language_dir):
        write_json(language_dir / "language.json", {"language": "he"})
        assert tr_module._read_language_file(language_dir / "language.json") == "he"

    def test_save_writes_v1_and_round_trips(self, language_dir):
        assert tr_module.save_language("he") is True
        assert read_json(language_dir / "language.json") == {"version": 1, "language": "he"}
        assert tr_module._read_language_file(language_dir / "language.json") == "he"

    def test_newer_version_is_read_and_kept_as_bak_on_save(self, language_dir):
        path = language_dir / "language.json"
        original = write_json(path, {"version": 2, "language": "he", "region": "IL"})
        assert tr_module._read_language_file(path) == "he"

        tr_module.save_language("en")
        assert (language_dir / "language.json.v2.bak").read_text(encoding="utf-8") == original
        assert read_json(path) == {"version": 1, "language": "en"}

    def test_damaged_file_is_kept_as_bad(self, language_dir):
        path = language_dir / "language.json"
        path.write_text("{oops", encoding="utf-8")
        assert tr_module._read_language_file(path) is None
        assert (language_dir / "language.json.bad").read_text(encoding="utf-8") == "{oops"

    def test_unknown_language_is_ignored(self, language_dir):
        write_json(language_dir / "language.json", {"version": 1, "language": "xx"})
        assert tr_module._read_language_file(language_dir / "language.json") is None
