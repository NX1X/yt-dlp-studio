"""
Versioned JSON files in the app data folder, and their migrations.

Every JSON file that the app keeps between runs has a top-level ``"version"``
key: the version of the file format (not the app version). This module reads
and writes these files with the same rules for all of them:

- **Missing ``"version"``:** the file is version 0 (the format before
  versioning). It is migrated in memory to the current version and written
  back on the next save.
- **Older version:** the migration functions run in order, one per version
  step, in memory. The file is written back on the next save.
- **Newer version** (written by a newer app): the caller loads what it
  understands and a warning is logged. Before the first write, a copy is kept
  as ``<name>.v<N>.bak``, so the newer data is never overwritten silently.
- **Damaged file** (unreadable, not JSON, wrong layout, bad version value, or
  a failed migration): a copy is kept as ``<name>.bad`` and the caller starts
  with defaults. A damaged file never stops the startup.

Add a format change like this:

1. Write a function that takes the data of version N and returns the data of
   version N + 1.
2. Append it to the ``migrations`` tuple of that file's ``FileFormat``. The
   current version is then one higher.
3. Add a test for the step, and update "File formats and migrations" in
   docs/ARCHITECTURE.md.

Never change or remove a migration that has shipped.
"""

import contextlib
import json
import os
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from .logger import get_logger

logger = get_logger()

# Name of the format version key in every file
VERSION_KEY = "version"

# One migration step: takes the data of version N, returns the data of N + 1.
# The version key is not in the data; the framework handles it.
Migration = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class FileFormat:
    """
    Format of one versioned JSON file.

    Attributes:
        name: Short name for log messages (for example "config")
        migrations: Ordered migration steps. ``migrations[i]`` upgrades
            version ``first_version + i`` to ``first_version + i + 1``.
        first_version: Oldest version that can be read. Files with a lower
            version, or without a version when this is above 0, are damaged.
    """

    name: str
    migrations: tuple[Migration, ...] = ()
    first_version: int = 0

    @property
    def current_version(self) -> int:
        """Version that this app writes."""
        return self.first_version + len(self.migrations)


class FileState(Enum):
    """Result of reading a versioned file."""

    MISSING = "missing"  # no file: start with defaults
    CURRENT = "current"  # current version, read as is
    MIGRATED = "migrated"  # older version, migrated in memory
    NEWER = "newer"  # newer version, data returned as it is in the file
    DAMAGED = "damaged"  # kept as <name>.bad (if it had content): start with defaults


@dataclass(frozen=True)
class LoadResult:
    """
    Data read from a versioned file.

    Attributes:
        state: What was found
        data: File content without the version key, at the current version
            (for NEWER: as it is in the file). None for MISSING and DAMAGED.
        file_version: Version found in the file (0 if it had no version
            key), or None if the file was missing or damaged
    """

    state: FileState
    data: dict[str, Any] | None = None
    file_version: int | None = None


# ----------------------------------------------------------------------
# Migrations, one tuple per file
# ----------------------------------------------------------------------


def _config_v0_to_v1(data: dict[str, Any]) -> dict[str, Any]:
    """Settings: version 1 adds only the version key. All fields stay."""
    return dict(data)


def _history_v0_to_v1(data: dict[str, Any]) -> dict[str, Any]:
    """History: version 1 adds only the version key ("max_entries" and "entries" stay)."""
    return dict(data)


def _language_v0_to_v1(data: dict[str, Any]) -> dict[str, Any]:
    """Language choice: version 1 adds only the version key ("language" stays)."""
    return dict(data)


# yt-dlp-studio_config.json (ConfigManager)
CONFIG_FORMAT = FileFormat("config", migrations=(_config_v0_to_v1,))
# download_history.json (HistoryManager)
HISTORY_FORMAT = FileFormat("history", migrations=(_history_v0_to_v1,))
# language.json (translations.save_language / load_saved_language)
LANGUAGE_FORMAT = FileFormat("language", migrations=(_language_v0_to_v1,))
# download_queue.json (QueueManager). It had a version from the start, so
# there is no version 0 and a file without a version is damaged.
QUEUE_FORMAT = FileFormat("queue", first_version=1)


# ----------------------------------------------------------------------
# Reading
# ----------------------------------------------------------------------


def bad_copy_path(path: Path) -> Path:
    """Path of the copy of a damaged file: ``<name>.bad``."""
    return path.with_name(path.name + ".bad")


def newer_backup_path(path: Path, version: int) -> Path:
    """Path of the copy of a file from a newer app: ``<name>.v<N>.bak``."""
    return path.with_name(f"{path.name}.v{version}.bak")


def keep_bad_copy(path: Path) -> None:
    """Keep a copy of a damaged file as ``<name>.bad``, so no data is lost silently."""
    bad_path = bad_copy_path(path)
    try:
        shutil.copyfile(path, bad_path)
        logger.warning(f"Kept a copy of the damaged file at {bad_path}")
    except OSError:
        logger.warning(f"Could not keep a copy of the damaged file at {bad_path}", exc_info=True)


def _damaged(path: Path, file_format: FileFormat, reason: str, keep_copy: bool = True) -> LoadResult:
    logger.warning(f"The {file_format.name} file {path} {reason}. Starting with defaults.")
    if keep_copy:
        keep_bad_copy(path)
    return LoadResult(FileState.DAMAGED)


def read_version(data: dict[str, Any]) -> int | None:
    """
    Return the format version of parsed file data.

    Returns:
        The version, 0 if there is no version key, or None if the value is
        not a non-negative int
    """
    if VERSION_KEY not in data:
        return 0
    version = data[VERSION_KEY]
    # type() check: True == 1 in Python, but a bool is not a version.
    if type(version) is not int or version < 0:
        return None
    return version


def migrate(data: dict[str, Any], file_format: FileFormat, from_version: int) -> dict[str, Any]:
    """
    Run the migration steps from ``from_version`` up to the current version.

    Args:
        data: File content without the version key
        file_format: Format of the file
        from_version: Version of ``data``, at least ``first_version``

    Returns:
        Data at the current version, without the version key

    Raises:
        ValueError: If ``from_version`` is outside the known range
        Exception: Whatever a migration step raises on bad data
    """
    if not file_format.first_version <= from_version <= file_format.current_version:
        raise ValueError(f"cannot migrate {file_format.name} from version {from_version}")
    for step in file_format.migrations[from_version - file_format.first_version :]:
        data = step(data)
        if not isinstance(data, dict):
            raise ValueError(f"{file_format.name} migration {step.__name__} did not return a dict")
    return data


def load_json_file(path: Path, file_format: FileFormat) -> LoadResult:
    """
    Read a versioned JSON file and migrate it to the current version.

    Never raises for a bad file: see the module docstring for the rules. An
    empty file counts as damaged, but no copy is kept (there is nothing to
    keep).

    Args:
        path: File to read
        file_format: Format of the file

    Returns:
        LoadResult with the state and the data
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.debug(f"No {file_format.name} file at {path}")
        return LoadResult(FileState.MISSING)
    except (OSError, UnicodeDecodeError):
        logger.debug(f"Could not read {path}", exc_info=True)
        return _damaged(path, file_format, "could not be read")

    if not raw.strip():
        return _damaged(path, file_format, "is empty", keep_copy=False)

    try:
        data = json.loads(raw)
    except (ValueError, RecursionError):  # JSONDecodeError, or nesting too deep
        return _damaged(path, file_format, "is not valid JSON")
    if not isinstance(data, dict):
        return _damaged(path, file_format, "has an unexpected layout")

    version = read_version(data)
    if version is None:
        return _damaged(path, file_format, f"has an invalid version {data.get(VERSION_KEY)!r}")
    if version < file_format.first_version:
        return _damaged(
            path,
            file_format,
            f"has version {version}, but the oldest known version is {file_format.first_version}",
        )

    content = {key: value for key, value in data.items() if key != VERSION_KEY}
    current = file_format.current_version

    if version > current:
        logger.warning(
            f"The {file_format.name} file {path} has version {version}, newer than this app "
            f"knows ({current}). Loading the parts this app understands. A copy is kept as "
            f"{newer_backup_path(path, version).name} before the file is saved."
        )
        return LoadResult(FileState.NEWER, content, version)

    if version == current:
        return LoadResult(FileState.CURRENT, content, version)

    try:
        content = migrate(content, file_format, version)
    except Exception:  # noqa: BLE001 - a bad file must never stop the startup
        logger.debug(f"Migration of {path} failed", exc_info=True)
        return _damaged(path, file_format, f"could not be migrated from version {version} to {current}")
    logger.info(f"Migrated the {file_format.name} file {path} from version {version} to {current} (saved on next save)")
    return LoadResult(FileState.MIGRATED, content, version)


# ----------------------------------------------------------------------
# Writing
# ----------------------------------------------------------------------


def write_text_atomic(path: Path, text: str) -> None:
    """
    Write text to path atomically.

    The temp file is in the same folder, so ``os.replace`` is a rename on
    the same file system and is atomic on Windows and Linux.

    Raises:
        OSError: If the write or the rename fails. The temp file is removed.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


def backup_newer_file(path: Path, file_format: FileFormat) -> None:
    """
    Keep a copy of ``path`` as ``<name>.v<N>.bak`` if a newer app wrote it.

    Call this before every write. It reads the file on disk, so it also
    works when the file was not read through ``load_json_file`` first. After
    the first write the file has the current version, and later calls do
    nothing. A missing or damaged file is left alone (a damaged file was
    already kept as ``.bad`` when it was read).

    Raises:
        OSError: If the copy fails. Do not write the file then, or the newer
            data would be lost.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError):
        return
    if not isinstance(data, dict):
        return
    version = read_version(data)
    if version is None or version <= file_format.current_version:
        return
    backup = newer_backup_path(path, version)
    shutil.copyfile(path, backup)
    logger.warning(f"Kept a copy of the {file_format.name} file from a newer app version at {backup}")


def save_json_file(path: Path, file_format: FileFormat, data: dict[str, Any], indent: int | None = 2) -> None:
    """
    Write data with the current version key, atomically.

    A file written by a newer app is copied to ``<name>.v<N>.bak`` first.

    Args:
        path: File to write
        file_format: Format of the file
        data: Content to write; a version key in it is replaced
        indent: JSON indent (None for one line)

    Raises:
        OSError: If the backup or the write fails
        TypeError, ValueError: If the data cannot be written as JSON
    """
    payload = {VERSION_KEY: file_format.current_version}
    payload.update((key, value) for key, value in data.items() if key != VERSION_KEY)
    text = json.dumps(payload, ensure_ascii=False, indent=indent)
    backup_newer_file(path, file_format)
    write_text_atomic(path, text)
