"""Tests for the per-playlist subtitle language picker.

These tests exercise the pure functions that resolve the user's checkbox /
text-input choices into a deduplicated list of yt-dlp language codes. The
full GUI path (PlaylistDialog instantiation, signal emission) is covered
separately by a Qt-using test.
"""

from __future__ import annotations

import pytest

from src.ui.playlist_dialog import (
    _SUBTITLE_LANGUAGE_CHOICES,
    _collect_subtitle_languages,
    _parse_extra_subtitle_codes,
)

# ---------- _parse_extra_subtitle_codes ----------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("", []),
        ("   ", []),
        ("pt", ["pt"]),
        ("pt,it", ["pt", "it"]),
        ("pt, it ,  zh-Hans", ["pt", "it", "zh-Hans"]),
        ("pt,pt,it,pt", ["pt", "it"]),
        (",pt,,it,", ["pt", "it"]),
    ],
)
def test_parse_extra_subtitle_codes(raw, expected):
    assert _parse_extra_subtitle_codes(raw) == expected


def test_parse_extra_subtitle_codes_accepts_none_like():
    # Defensive: callers may pass an empty placeholder string.
    assert _parse_extra_subtitle_codes("") == []


# ---------- _collect_subtitle_languages ----------


def test_collect_subtitle_languages_empty_returns_empty():
    assert _collect_subtitle_languages([], "") == []


def test_collect_hebrew_expands_to_he_and_iw():
    """Hebrew is special - YouTube serves it under both `he` and `iw`."""
    assert _collect_subtitle_languages(["he"], "") == ["he", "iw"]


def test_collect_english_is_single_code():
    assert _collect_subtitle_languages(["en"], "") == ["en"]


def test_collect_preserves_user_order_he_first():
    """Order of the checkboxes is the order the codes flow into yt-dlp."""
    out = _collect_subtitle_languages(["he", "en"], "")
    assert out == ["he", "iw", "en"]


def test_collect_preserves_user_order_en_first():
    out = _collect_subtitle_languages(["en", "he"], "")
    assert out == ["en", "he", "iw"]


def test_collect_merges_extra_codes():
    out = _collect_subtitle_languages(["he"], "pt, it")
    assert out == ["he", "iw", "pt", "it"]


def test_collect_deduplicates_across_presets_and_extras():
    """A user who ticks Hebrew AND types `iw` should not see `iw` twice."""
    out = _collect_subtitle_languages(["he"], "iw, pt, he")
    assert out == ["he", "iw", "pt"]


def test_collect_unknown_preset_keys_are_ignored():
    """A key not in _SUBTITLE_LANGUAGE_CHOICES must not crash or appear in output."""
    out = _collect_subtitle_languages(["he", "klingon", "en"], "")
    assert out == ["he", "iw", "en"]


def test_collect_handles_extras_only():
    out = _collect_subtitle_languages([], "ja, ko")
    assert out == ["ja", "ko"]


# ---------- _SUBTITLE_LANGUAGE_CHOICES integrity ----------


def test_hebrew_choice_maps_to_both_codes():
    """The Hebrew preset is the only multi-code mapping; protect it explicitly."""
    he = {key: codes for key, _, codes in _SUBTITLE_LANGUAGE_CHOICES}
    assert he["he"] == ("he", "iw")


def test_all_choices_have_translation_keys():
    """Each preset must point at a translation key the UI can look up."""
    from src.utils.translations import TRANSLATIONS

    en = TRANSLATIONS["en"]
    he = TRANSLATIONS["he"]
    for _key, tr_key, _codes in _SUBTITLE_LANGUAGE_CHOICES:
        assert tr_key in en, f"missing English translation: {tr_key}"
        assert tr_key in he, f"missing Hebrew translation: {tr_key}"


def test_choice_keys_are_unique():
    keys = [key for key, _, _ in _SUBTITLE_LANGUAGE_CHOICES]
    assert len(set(keys)) == len(keys), "duplicate language key in preset list"


def test_hebrew_appears_first():
    """The app's primary audience is Hebrew-speaking; Hebrew gets top placement."""
    first_key = _SUBTITLE_LANGUAGE_CHOICES[0][0]
    assert first_key == "he"
