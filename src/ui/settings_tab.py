"""
Settings tab UI for YT-DLP Studio.

Provides interface for configuring application settings. The groups sit in a
scroll area; the Reset and Save buttons sit in a bar below it that never
scrolls away.
"""

from datetime import UTC, datetime
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from ..backend.config_manager import ConfigManager
from ..backend.format_handler import FormatHandler
from ..utils.constants import APP_VERSION, CONFIG_PATH, LOG_PATH, QUALITY_NAMES
from ..utils.crash_handler import get_crash_dir
from ..utils.logger import get_logger
from ..utils.translations import get_translation_manager, save_language, tr
from .advanced_download_options import AdvancedDownloadOptions
from .status_messages import show_status
from .theme import ThemeMode, get_theme_manager

logger = get_logger()


class SettingsTab(QWidget):
    """
    Settings tab widget.

    Allows users to configure:
    - Default output directory and quality
    - Theme and language
    - Notifications, tray and update checks
    - Advanced download options
    It also shows the files a bug report needs.

    Example:
        >>> tab = SettingsTab(config_manager)
    """

    # Signal emitted when default folder changes (v1.9.0)
    default_folder_changed = Signal(str)

    # Emitted with the saved value after a save or a reset, so the main
    # window can apply it to the NotificationManager.
    notifications_enabled_changed = Signal(bool)

    # Emitted with the saved value after a save or a reset, so the main
    # window can switch hide-to-tray on or off.
    close_to_tray_changed = Signal(bool)

    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        Initialize settings tab.

        Args:
            config_manager: ConfigManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.config_manager = config_manager
        # Labels of all forms, so the label columns of the groups line up.
        self._form_labels: list[QLabel] = []
        self._setup_ui()
        self._load_settings()
        logger.info("SettingsTab initialized")

    # ------------------------------------------------------------------ UI

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        scroll_area.setWidget(content)
        outer_layout.addWidget(scroll_area, 1)

        main_layout = QVBoxLayout(content)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        main_layout.addWidget(self._build_downloads_group())
        main_layout.addWidget(self._build_appearance_group())
        main_layout.addWidget(self._build_behavior_group())

        # Advanced download options (0.5.0): cookies, proxy, file names, formats
        self.advanced_options = AdvancedDownloadOptions()
        main_layout.addWidget(self.advanced_options)

        main_layout.addWidget(self._build_bug_report_files_group())
        main_layout.addStretch()

        self._align_form_labels()
        outer_layout.addWidget(self._build_button_bar())

    def _form(self, group: QGroupBox) -> QFormLayout:
        form = QFormLayout(group)
        form.setContentsMargins(12, 8, 12, 12)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeading | Qt.AlignmentFlag.AlignVCenter)
        return form

    def _add_row(self, form: QFormLayout, label_text: str, field: QWidget, buddy: QWidget | None = None) -> QLabel:
        label = QLabel(label_text)
        label.setBuddy(buddy or field)
        self._form_labels.append(label)
        form.addRow(label, field)
        return label

    @staticmethod
    def _row(*widgets: QWidget, stretch: bool = False) -> QWidget:
        """Put widgets side by side in one form field."""
        row = QWidget()
        # The theme keeps #formRow transparent, so the group color shows through.
        row.setObjectName("formRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        for widget in widgets:
            layout.addWidget(widget)
        if stretch:
            layout.addStretch()
        return row

    def _build_downloads_group(self) -> QGroupBox:
        group = QGroupBox(tr("settings_downloads"))
        form = self._form(group)

        self.output_input = QLineEdit()
        self.output_input.setReadOnly(True)
        self.output_input.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.browse_button = QPushButton(tr("button_browse"))
        self.browse_button.clicked.connect(self._browse_directory)
        self._add_row(
            form, tr("label_default_folder"), self._row(self.output_input, self.browse_button), self.browse_button
        )

        # Items carry the stable quality key; the text is translated.
        self.quality_combo = QComboBox()
        for key, label in zip(QUALITY_NAMES, FormatHandler.get_available_qualities(), strict=True):
            self.quality_combo.addItem(label, key)
        self._add_row(
            form, tr("label_default_quality"), self._row(self.quality_combo, stretch=True), self.quality_combo
        )
        return group

    def _build_appearance_group(self) -> QGroupBox:
        group = QGroupBox(tr("settings_appearance"))
        form = self._form(group)

        # The theme applies at once and is saved at once.
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(tr("theme_dark"), ThemeMode.DARK.value)
        self.theme_combo.addItem(tr("theme_light"), ThemeMode.LIGHT.value)
        self.theme_combo.setToolTip(tr("tooltip_theme_combo"))
        self.theme_combo.currentIndexChanged.connect(self._on_theme_selected)
        self._add_row(form, tr("label_theme"), self._row(self.theme_combo, stretch=True), self.theme_combo)

        self.language_combo = QComboBox()
        tm = get_translation_manager()
        for code, name in tm.get_available_languages().items():
            self.language_combo.addItem(name, code)
        index = self.language_combo.findData(tm.get_language())
        if index >= 0:
            self.language_combo.setCurrentIndex(index)
        self._add_row(form, tr("label_language"), self._row(self.language_combo, stretch=True), self.language_combo)
        # The restart note sits under the field, in the field column.
        language_hint = QLabel(tr("label_language_restart_hint"))
        language_hint.setProperty("labelStyle", "secondary")
        language_hint.setWordWrap(True)
        form.addRow("", language_hint)
        return group

    def _build_behavior_group(self) -> QGroupBox:
        group = QGroupBox(tr("settings_behavior"))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(8)

        self.notifications_checkbox = QCheckBox(tr("checkbox_notifications"))
        self.notifications_checkbox.setChecked(True)
        self.notifications_checkbox.setToolTip(tr("tooltip_notifications"))
        layout.addWidget(self.notifications_checkbox)

        # Keep running in the tray on close. Without a system tray (for
        # example stock GNOME) the window could not come back, so the
        # option is disabled and the tooltip says why.
        self.close_to_tray_checkbox = QCheckBox(tr("checkbox_close_to_tray"))
        self.close_to_tray_checkbox.setChecked(False)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.close_to_tray_checkbox.setToolTip(tr("tooltip_close_to_tray"))
        else:
            self.close_to_tray_checkbox.setEnabled(False)
            self.close_to_tray_checkbox.setToolTip(tr("tooltip_close_to_tray_unavailable"))
        layout.addWidget(self.close_to_tray_checkbox)

        # Update check on startup, with the manual check next to it
        self.auto_update_checkbox = QCheckBox(tr("checkbox_auto_update"))
        self.auto_update_checkbox.setChecked(True)
        self.auto_update_checkbox.setToolTip(tr("tooltip_auto_update"))
        self.check_update_button = QPushButton(tr("button_check_for_updates_now"))
        self.check_update_button.clicked.connect(self._check_for_updates)
        update_row = QHBoxLayout()
        update_row.setSpacing(16)
        update_row.addWidget(self.auto_update_checkbox)
        update_row.addWidget(self.check_update_button)
        update_row.addStretch()
        layout.addLayout(update_row)
        return group

    def _build_bug_report_files_group(self) -> QGroupBox:
        """The paths a bug report needs, each with Copy and Open folder."""
        group = QGroupBox(tr("settings_bug_report_files"))
        form = self._form(group)

        for label_key, path_value, folder in (
            ("label_log_file_path", str(LOG_PATH), Path(LOG_PATH).parent),
            ("label_crash_dir_path", str(get_crash_dir()), Path(get_crash_dir())),
            ("label_config_file_path", str(CONFIG_PATH), Path(CONFIG_PATH).parent),
        ):
            path_field = QLineEdit(path_value)
            path_field.setReadOnly(True)
            path_field.setCursorPosition(0)
            path_field.setToolTip(path_value)
            path_field.setAccessibleName(tr(label_key).rstrip(":\u200f"))  # also the RLM that tr() adds in Hebrew
            copy_button = QPushButton(tr("button_copy"))
            copy_button.setToolTip(tr("tooltip_copy_path"))
            copy_button.clicked.connect(lambda _checked=False, p=path_value: self._copy_path(p))
            open_button = QPushButton(tr("button_settings_open_folder"))
            open_button.setToolTip(tr("tooltip_settings_open_folder"))
            open_button.clicked.connect(lambda _checked=False, f=folder: self._open_folder(f))
            self._add_row(form, tr(label_key), self._row(path_field, copy_button, open_button), path_field)
        return group

    def _build_button_bar(self) -> QWidget:
        """Reset (start side) and Save (end side), outside the scroll area."""
        bar = QFrame()
        bar.setObjectName("settingsButtonBar")
        bar.setFrameShape(QFrame.Shape.NoFrame)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 8, 16, 8)

        self.reset_button = QPushButton(tr("button_reset_defaults"))
        self.reset_button.clicked.connect(self._reset_defaults)
        layout.addWidget(self.reset_button)
        layout.addStretch()

        self.save_button = QPushButton(tr("button_save_settings"))
        self.save_button.setProperty("buttonStyle", "primary")
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self._save_settings)
        layout.addWidget(self.save_button)
        return bar

    def _align_form_labels(self) -> None:
        """Give all form labels the width of the widest, so fields line up."""
        width = max((label.sizeHint().width() for label in self._form_labels), default=0)
        for label in self._form_labels:
            label.setMinimumWidth(width)

    # ---------------------------------------------------------------- data

    def _load_settings(self) -> None:
        """Load current settings from config."""
        config = self.config_manager.get_config()
        self.output_input.setText(config.output_directory)
        self.output_input.setCursorPosition(0)
        index = self.quality_combo.findData(config.default_quality)
        if index < 0:
            # Older versions saved the translated label.
            index = max(self.quality_combo.findText(config.default_quality), 0)
        self.quality_combo.setCurrentIndex(index)
        self.theme_combo.blockSignals(True)
        self.theme_combo.setCurrentIndex(max(self.theme_combo.findData(ThemeMode.from_value(config.theme).value), 0))
        self.theme_combo.blockSignals(False)
        self.auto_update_checkbox.setChecked(config.check_updates_on_startup)
        self.notifications_checkbox.setChecked(config.notifications_enabled)
        self.close_to_tray_checkbox.setChecked(config.close_to_tray)
        self.advanced_options.load(config)
        logger.debug("Settings loaded into UI")

    def _browse_directory(self) -> None:
        """Open directory browser dialog."""
        current_dir = self.output_input.text()
        directory = QFileDialog.getExistingDirectory(self, tr("dialog_select_default_download_dir"), current_dir)

        if directory:
            self.output_input.setText(directory)
            logger.debug(f"Directory selected: {directory}")

    def _save_settings(self) -> None:
        """Save settings to config."""
        output_dir = self.output_input.text()
        default_quality = self.quality_combo.currentData() or QUALITY_NAMES[0]

        # Get selected language
        selected_lang_code = self.language_combo.currentData()
        tm = get_translation_manager()
        current_lang = tm.get_language()
        language_changed = selected_lang_code != current_lang

        # Validate
        from ..utils.validators import Validators

        is_valid, error = Validators.is_valid_directory(output_dir)
        if not is_valid:
            QMessageBox.warning(self, tr("error_invalid_directory"), error)
            return

        advanced_error = self.advanced_options.validation_error()
        if advanced_error:
            QMessageBox.warning(self, tr("error_invalid_advanced_settings"), advanced_error)
            return

        # Save language preference
        if language_changed:
            # Saved in the app data folder (see utils/translations.py)
            save_language(selected_lang_code)

        # Save other settings
        old_output_dir = self.config_manager.get_config().output_directory
        success = self.config_manager.update_config(
            output_directory=output_dir,
            default_quality=default_quality,
            check_updates_on_startup=self.auto_update_checkbox.isChecked(),
            notifications_enabled=self.notifications_checkbox.isChecked(),
            close_to_tray=self.close_to_tray_checkbox.isChecked(),
            **self.advanced_options.config_values(),
        )

        if success:
            logger.info("Settings saved successfully")
            self.notifications_enabled_changed.emit(self.notifications_checkbox.isChecked())
            self.close_to_tray_changed.emit(self.close_to_tray_checkbox.isChecked())

            # Emit signal if folder changed (v1.9.0 smart folder logic)
            if output_dir != old_output_dir:
                self.default_folder_changed.emit(output_dir)
                logger.info(f"Default folder changed signal emitted: {output_dir}")

            if language_changed:
                # A restart is needed, so this one stays a message box.
                QMessageBox.information(
                    self,
                    tr("dialog_settings_saved_restart_required"),
                    tr("msg_language_changed_restart_required", language=self.language_combo.currentText()),
                )
            else:
                show_status(self, tr("status_settings_saved"))
        else:
            logger.error("Failed to save settings")
            QMessageBox.critical(self, tr("error_generic"), tr("msg_failed_save_settings"))

    def _reset_defaults(self) -> None:
        """Reset settings to defaults."""
        reply = QMessageBox.question(
            self,
            tr("dialog_reset_settings"),
            tr("msg_confirm_reset_settings"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.config_manager.reset_to_defaults()
            self._load_settings()
            self._apply_theme(self.config_manager.get_config().theme)
            self.notifications_enabled_changed.emit(self.notifications_checkbox.isChecked())
            self.close_to_tray_changed.emit(self.close_to_tray_checkbox.isChecked())
            logger.info("Settings reset to defaults")
            show_status(self, tr("msg_all_settings_reset"))

    def _check_for_updates(self) -> None:
        """Check for application updates without blocking the UI thread."""
        from ..ui.update_dialog import UpdateCheckThread

        self.check_update_button.setEnabled(False)
        self.check_update_button.setText(tr("button_checking"))

        # Keep a reference so the thread is not garbage collected mid-run.
        self._update_check_thread = UpdateCheckThread(self)
        self._update_check_thread.check_complete.connect(self._on_update_check_finished)
        self._update_check_thread.start()

    def _on_update_check_finished(self, result) -> None:
        """
        Handle a manual update check result.

        A manual check is an explicit user action, so it always surfaces an
        available update even if that version was previously skipped.
        """
        from ..ui.update_dialog import UpdateDialog

        self.check_update_button.setEnabled(True)
        self.check_update_button.setText(tr("button_check_for_updates_now"))

        if result.error:
            logger.error(f"Update check failed: {result.error}")
            if result.error == "rate_limited":
                QMessageBox.warning(self, tr("dialog_update_check_failed"), tr("msg_update_check_rate_limited"))
            else:
                QMessageBox.warning(
                    self, tr("dialog_update_check_failed"), tr("msg_update_check_failed", error=result.error)
                )
            return

        self.config_manager.update_config(last_update_check=datetime.now(UTC).isoformat())

        if result.update_available and result.release_info:
            logger.info(f"Update available: {result.release_info['version']}")
            dialog = UpdateDialog(result.release_info, self, self.config_manager)
            dialog.exec()
        else:
            logger.info("No updates available")
            QMessageBox.information(
                self, tr("dialog_no_updates"), tr("msg_already_latest_version", version=APP_VERSION)
            )

    # --------------------------------------------------------------- theme

    def _on_theme_selected(self, _index: int) -> None:
        """Apply the chosen theme at once and save it."""
        mode = self.theme_combo.currentData()
        self._apply_theme(mode)
        self.config_manager.update_config(theme=mode)

    @staticmethod
    def _apply_theme(value: str) -> None:
        theme_manager = get_theme_manager()
        mode = ThemeMode.from_value(value)
        if mode != theme_manager.get_current_mode():
            theme_manager.apply_theme(mode)
            logger.info(f"Theme changed to: {mode.value}")

    def _toggle_theme(self) -> None:
        """Switch between the dark and the light theme (saved at once)."""
        self.theme_combo.setCurrentIndex(1 - self.theme_combo.currentIndex())

    # --------------------------------------------------------------- files

    def _copy_path(self, path: str) -> None:
        """Copy a path to the clipboard and confirm it in the status bar."""
        clipboard = QApplication.clipboard()
        if clipboard is None:
            return
        clipboard.setText(path)
        logger.debug(f"Copied path to clipboard: {path}")
        show_status(self, tr("msg_path_copied"))

    def _open_folder(self, folder: Path) -> None:
        """Open a folder in the file manager (it may not exist yet)."""
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning(f"Could not create {folder}: {e}")
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder))):
            logger.warning(f"Could not open folder: {folder}")
