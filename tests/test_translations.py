"""Tests for src/utils/translations.py."""

import pytest

from src.utils.translations import TRANSLATIONS, TranslationManager, get_translation_manager, tr


@pytest.fixture(autouse=True)
def reset_translation_singleton():
    """Reset the global translation manager between tests."""
    import src.utils.translations as mod

    mod._translation_manager = None
    yield
    mod._translation_manager = None


class TestTranslationManagerInit:
    """Tests for TranslationManager initialization."""

    def test_defaults_to_english_or_he(self):
        tm = TranslationManager()
        assert tm.current_language in ("en", "he")


class TestSetLanguage:
    """Tests for TranslationManager.set_language()."""

    def test_set_to_hebrew(self):
        tm = TranslationManager()
        tm.set_language("he")
        assert tm.get_language() == "he"

    def test_set_to_english(self):
        tm = TranslationManager()
        tm.set_language("he")
        tm.set_language("en")
        assert tm.get_language() == "en"

    def test_set_invalid_keeps_current(self):
        tm = TranslationManager()
        tm.set_language("en")
        tm.set_language("xx")
        assert tm.get_language() == "en"


class TestTranslate:
    """Tests for TranslationManager.translate()."""

    def test_english_key(self):
        tm = TranslationManager()
        tm.set_language("en")
        result = tm.translate("tab_download")
        assert result == "Download"

    def test_hebrew_key(self):
        tm = TranslationManager()
        tm.set_language("he")
        result = tm.translate("tab_download")
        assert result == "הורדה"

    def test_unknown_key_returns_key(self):
        tm = TranslationManager()
        tm.set_language("en")
        result = tm.translate("nonexistent_key_xyz")
        assert result == "nonexistent_key_xyz"

    def test_with_format_params(self):
        tm = TranslationManager()
        tm.set_language("en")
        result = tm.translate("batch_count", count=5)
        assert "5" in result


class TestRTL:
    """Tests for RTL detection."""

    def test_english_not_rtl(self):
        tm = TranslationManager()
        tm.set_language("en")
        assert tm.is_rtl() is False

    def test_hebrew_is_rtl(self):
        tm = TranslationManager()
        tm.set_language("he")
        assert tm.is_rtl() is True


class TestAvailableLanguages:
    """Tests for get_available_languages()."""

    def test_returns_dict(self):
        tm = TranslationManager()
        langs = tm.get_available_languages()
        assert isinstance(langs, dict)
        assert "en" in langs
        assert "he" in langs


class TestTranslationCompleteness:
    """Tests to verify all keys exist in both languages."""

    def test_all_english_keys_exist_in_hebrew(self):
        en_keys = set(TRANSLATIONS["en"].keys())
        he_keys = set(TRANSLATIONS["he"].keys())
        missing = en_keys - he_keys
        assert missing == set(), f"Missing Hebrew translations: {missing}"

    def test_all_hebrew_keys_exist_in_english(self):
        en_keys = set(TRANSLATIONS["en"].keys())
        he_keys = set(TRANSLATIONS["he"].keys())
        extra = he_keys - en_keys
        assert extra == set(), f"Extra Hebrew keys not in English: {extra}"


class TestShorthandFunction:
    """Tests for the tr() shorthand function."""

    def test_tr_returns_string(self):
        result = tr("tab_download")
        assert isinstance(result, str)
        assert len(result) > 0


class TestGetTranslationManager:
    """Tests for singleton behavior."""

    def test_returns_same_instance(self):
        tm1 = get_translation_manager()
        tm2 = get_translation_manager()
        assert tm1 is tm2
