"""
Advanced download options for the Settings tab.

One collapsible section with the 0.5.0 options: browser cookies, proxy, file
name template and format options. It only shows and checks the values; the
Settings tab saves them with the other settings (see ``config_values``).
"""

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..backend.download_options import (
    CODEC_ANY,
    FILENAME_PRESET_CUSTOM,
    FILENAME_PRESET_DATE_TITLE,
    FILENAME_PRESET_TITLE_QUALITY,
    FILENAME_PRESET_UPLOADER_TITLE,
)
from ..backend.download_preferences import (
    browser_display_name,
    cookie_browsers,
    validate_cookies_profile,
    validate_custom_format,
    validate_filename_template,
    validate_proxy_url,
)
from ..models.app_config import AppConfig
from ..utils.translations import tr
from .help_links import ANCHOR_ADVANCED_OPTIONS, make_help_button

# Codec names are product names; only "Any" is translated.
_VIDEO_CODECS = (("h264", "H.264"), ("h265", "H.265 / HEVC"), ("vp9", "VP9"), ("av1", "AV1"))
_AUDIO_CODECS = (("aac", "AAC"), ("opus", "Opus"), ("vorbis", "Vorbis"))
_FILENAME_PRESETS = (
    (FILENAME_PRESET_TITLE_QUALITY, "filename_preset_title_quality"),
    (FILENAME_PRESET_UPLOADER_TITLE, "filename_preset_uploader_title"),
    (FILENAME_PRESET_DATE_TITLE, "filename_preset_date_title"),
    (FILENAME_PRESET_CUSTOM, "filename_preset_custom"),
)


class AdvancedDownloadOptions(QWidget):
    """A show/hide button and the group of advanced download options."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._update_enabled_fields()

    # ---------- layout ----------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.toggle_button = QPushButton(tr("button_show_advanced_download"))
        self.toggle_button.setCheckable(True)
        self.toggle_button.setProperty("buttonStyle", "secondary")
        self.toggle_button.setToolTip(tr("tooltip_toggle_advanced_download"))
        self.toggle_button.toggled.connect(self._set_expanded)
        layout.addWidget(self.toggle_button)

        self.group = QGroupBox(tr("settings_advanced_download"))
        form = QFormLayout()
        self._add_cookie_rows(form)
        self._add_proxy_row(form)
        self._add_filename_rows(form)
        self._add_format_rows(form)
        applies = QLabel(tr("text_advanced_applies"))
        applies.setWordWrap(True)
        applies.setProperty("labelStyle", "secondary")
        form.addRow(applies)
        help_row = QHBoxLayout()
        help_row.addStretch(1)
        help_row.addWidget(make_help_button(ANCHOR_ADVANCED_OPTIONS))
        form.addRow(help_row)
        self.group.setLayout(form)
        self.group.setVisible(False)
        layout.addWidget(self.group)

    def _add_row(self, form: QFormLayout, label_key: str, field: QWidget, tooltip_key: str) -> None:
        label = QLabel(tr(label_key))
        label.setBuddy(field)  # screen readers announce the label with the field
        field.setAccessibleName(tr(label_key).rstrip(":\u200f"))  # also the RLM that tr() adds in Hebrew
        field.setToolTip(tr(tooltip_key))
        form.addRow(label, field)

    def _add_cookie_rows(self, form: QFormLayout) -> None:
        self.cookies_combo = QComboBox()
        self.cookies_combo.addItem(tr("cookies_browser_none"), "")
        for browser in cookie_browsers():
            self.cookies_combo.addItem(browser_display_name(browser), browser)
        self.cookies_combo.currentIndexChanged.connect(self._update_enabled_fields)
        self._add_row(form, "label_cookies_browser", self.cookies_combo, "tooltip_cookies_browser")

        self.cookies_profile_input = QLineEdit()
        self.cookies_profile_input.setPlaceholderText(tr("placeholder_cookies_profile"))
        self._add_row(form, "label_cookies_profile", self.cookies_profile_input, "tooltip_cookies_profile")

        privacy = QLabel(tr("text_cookies_privacy"))
        privacy.setWordWrap(True)
        privacy.setProperty("labelStyle", "secondary")
        form.addRow(privacy)

    def _add_proxy_row(self, form: QFormLayout) -> None:
        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText(tr("placeholder_proxy"))
        self._add_row(form, "label_proxy", self.proxy_input, "tooltip_proxy")

    def _add_filename_rows(self, form: QFormLayout) -> None:
        self.filename_combo = QComboBox()
        for preset, key in _FILENAME_PRESETS:
            self.filename_combo.addItem(tr(key), preset)
        self.filename_combo.currentIndexChanged.connect(self._update_enabled_fields)
        self._add_row(form, "label_filename_template", self.filename_combo, "tooltip_filename_template")

        self.custom_template_input = QLineEdit()
        self.custom_template_input.setPlaceholderText(tr("placeholder_custom_template"))
        self._add_row(form, "label_custom_template", self.custom_template_input, "tooltip_custom_template")

    def _add_format_rows(self, form: QFormLayout) -> None:
        self.video_codec_combo = self._codec_combo(_VIDEO_CODECS)
        self._add_row(form, "label_video_codec", self.video_codec_combo, "tooltip_video_codec")
        self.audio_codec_combo = self._codec_combo(_AUDIO_CODECS)
        self._add_row(form, "label_audio_codec", self.audio_codec_combo, "tooltip_audio_codec")

        self.custom_format_input = QLineEdit()
        self.custom_format_input.setPlaceholderText(tr("placeholder_custom_format"))
        self.custom_format_input.textChanged.connect(self._update_enabled_fields)
        self._add_row(form, "label_custom_format", self.custom_format_input, "tooltip_custom_format")

    @staticmethod
    def _codec_combo(codecs: tuple[tuple[str, str], ...]) -> QComboBox:
        combo = QComboBox()
        combo.addItem(tr("codec_any"), CODEC_ANY)
        for value, name in codecs:
            combo.addItem(name, value)
        return combo

    # ---------- state ----------

    def _set_expanded(self, expanded: bool) -> None:
        self.group.setVisible(expanded)
        key = "button_hide_advanced_download" if expanded else "button_show_advanced_download"
        self.toggle_button.setText(tr(key))

    def _update_enabled_fields(self) -> None:
        self.cookies_profile_input.setEnabled(bool(self.cookies_combo.currentData()))
        self.custom_template_input.setEnabled(self.filename_combo.currentData() == FILENAME_PRESET_CUSTOM)
        # A custom format string replaces the codec choices.
        uses_codecs = not self.custom_format_input.text().strip()
        self.video_codec_combo.setEnabled(uses_codecs)
        self.audio_codec_combo.setEnabled(uses_codecs)

    @staticmethod
    def _select(combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        combo.setCurrentIndex(index if index >= 0 else 0)

    def load(self, config: AppConfig) -> None:
        """Show the values of ``config``. An unknown value shows the first item."""
        self._select(self.cookies_combo, config.cookies_browser)
        self.cookies_profile_input.setText(config.cookies_profile)
        self.proxy_input.setText(config.proxy_url)
        self._select(self.filename_combo, config.filename_template_preset)
        self.custom_template_input.setText(config.custom_filename_template)
        self._select(self.video_codec_combo, config.video_codec_preference)
        self._select(self.audio_codec_combo, config.audio_codec_preference)
        self.custom_format_input.setText(config.custom_format)
        self._update_enabled_fields()

    def config_values(self) -> dict[str, str]:
        """The values as ``AppConfig`` fields, for ``ConfigManager.update_config``."""
        return {
            "cookies_browser": self.cookies_combo.currentData() or "",
            "cookies_profile": self.cookies_profile_input.text().strip(),
            "proxy_url": self.proxy_input.text().strip(),
            "filename_template_preset": self.filename_combo.currentData(),
            "custom_filename_template": self.custom_template_input.text().strip(),
            "video_codec_preference": self.video_codec_combo.currentData(),
            "audio_codec_preference": self.audio_codec_combo.currentData(),
            "custom_format": self.custom_format_input.text().strip(),
        }

    def validation_error(self) -> str | None:
        """A translated message for the first invalid value, or None.

        Opens the section and puts the focus on the field, so the user sees
        what to fix.
        """
        values = self.config_values()
        checks = [
            (self.cookies_profile_input, validate_cookies_profile(values["cookies_profile"])),
            (self.proxy_input, validate_proxy_url(values["proxy_url"])),
        ]
        if values["filename_template_preset"] == FILENAME_PRESET_CUSTOM:
            checks.append((self.custom_template_input, validate_filename_template(values["custom_filename_template"])))
        checks.append((self.custom_format_input, self._format_error(values["custom_format"])))
        for field, key in checks:
            if key:
                self.toggle_button.setChecked(True)
                field.setFocus()
                return tr(key)
        return None

    @staticmethod
    def _format_error(format_string: str) -> str | None:
        key = validate_custom_format(format_string)
        if key or not format_string:
            return key
        # Let yt-dlp parse it, too (no network).
        from ..backend.yt_dlp_wrapper import YtDlpWrapper

        return "error_format_syntax" if YtDlpWrapper.format_selector_error(format_string) else None
