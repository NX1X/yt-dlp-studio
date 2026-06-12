"""
Settings tab UI for YT-DLP Studio.

Provides interface for configuring application settings.
"""

from datetime import datetime, timezone

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..backend.config_manager import ConfigManager
from ..backend.format_handler import FormatHandler
from ..utils.constants import APP_VERSION, CONFIG_PATH, LOG_PATH
from ..utils.crash_handler import get_crash_dir
from ..utils.logger import get_logger
from ..utils.translations import get_translation_manager, tr

logger = get_logger()


class SettingsTab(QWidget):
    """
    Settings tab widget.

    Allows users to configure:
    - Default output directory
    - Default quality setting
    - View application info

    Example:
        >>> tab = SettingsTab(config_manager)
    """

    # Signal emitted when default folder changes (v1.9.0)
    default_folder_changed = Signal(str)

    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        Initialize settings tab.

        Args:
            config_manager: ConfigManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self._setup_ui()
        self._load_settings()
        logger.info("SettingsTab initialized")

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        main_layout = QVBoxLayout(self)

        # General settings group
        general_group = QGroupBox(tr("settings_general"))
        general_layout = QVBoxLayout()

        # Default output directory
        output_layout = QHBoxLayout()
        output_label = QLabel(tr("label_default_folder"))
        output_label.setMinimumWidth(180)
        self.output_input = QLineEdit()
        self.output_input.setReadOnly(True)
        self.browse_button = QPushButton(tr("button_browse"))
        self.browse_button.clicked.connect(self._browse_directory)
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_input)
        output_layout.addWidget(self.browse_button)
        general_layout.addLayout(output_layout)

        # Default quality
        quality_layout = QHBoxLayout()
        quality_label = QLabel(tr("label_default_quality"))
        quality_label.setMinimumWidth(180)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(FormatHandler.get_available_qualities())
        quality_layout.addWidget(quality_label)
        quality_layout.addWidget(self.quality_combo)
        quality_layout.addStretch()
        general_layout.addLayout(quality_layout)

        # Language selector (v1.7.0)
        language_layout = QHBoxLayout()
        language_label = QLabel(tr("label_language"))
        language_label.setMinimumWidth(180)
        self.language_combo = QComboBox()
        tm = get_translation_manager()
        languages = tm.get_available_languages()
        for code, name in languages.items():
            self.language_combo.addItem(name, code)
        # Set current language
        current_lang = tm.get_language()
        index = self.language_combo.findData(current_lang)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)
        language_layout.addWidget(language_label)
        language_layout.addWidget(self.language_combo)
        language_layout.addStretch()
        general_layout.addLayout(language_layout)

        general_group.setLayout(general_layout)
        main_layout.addWidget(general_group)

        # Appearance settings (v2.0.0 - moved from menu bar)
        appearance_group = QGroupBox(tr("settings_appearance"))
        appearance_layout = QVBoxLayout()

        # Theme toggle button. Inline `background-color: #4a4a4a` was
        # hardcoded dark-theme grey and bypassed the theme manager - replaced
        # with the buttonStyle="secondary" property so the QSS in theme.py
        # picks the right shade for both light and dark.
        theme_button_layout = QHBoxLayout()
        theme_label = QLabel(tr("label_theme"))
        theme_label.setMinimumWidth(180)
        self.toggle_theme_button = QPushButton(tr("button_toggle_theme"))
        self.toggle_theme_button.setMinimumWidth(180)
        self.toggle_theme_button.setToolTip(tr("tooltip_toggle_theme"))
        self.toggle_theme_button.setProperty("buttonStyle", "secondary")
        self.toggle_theme_button.clicked.connect(self._toggle_theme)
        theme_button_layout.addWidget(theme_label)
        theme_button_layout.addWidget(self.toggle_theme_button)
        theme_button_layout.addStretch()
        appearance_layout.addLayout(theme_button_layout)

        appearance_group.setLayout(appearance_layout)
        main_layout.addWidget(appearance_group)

        # Notifications & Updates (v1.7.0)
        features_group = QGroupBox(tr("settings_features"))
        features_layout = QVBoxLayout()

        # Enable notifications checkbox
        self.notifications_checkbox = QCheckBox(tr("checkbox_notifications"))
        self.notifications_checkbox.setChecked(True)
        self.notifications_checkbox.setToolTip(tr("tooltip_notifications"))
        features_layout.addWidget(self.notifications_checkbox)

        # Auto-check updates checkbox
        self.auto_update_checkbox = QCheckBox(tr("checkbox_auto_update"))
        self.auto_update_checkbox.setChecked(True)
        self.auto_update_checkbox.setToolTip(tr("tooltip_auto_update"))
        features_layout.addWidget(self.auto_update_checkbox)

        # Check-for-updates button uses the secondary style for the same
        # palette-aware reason as the theme toggle above.
        update_button_layout = QHBoxLayout()
        self.check_update_button = QPushButton(tr("button_check_update"))
        self.check_update_button.setMinimumWidth(180)
        self.check_update_button.setProperty("buttonStyle", "secondary")
        self.check_update_button.clicked.connect(self._check_for_updates)
        update_button_layout.addWidget(self.check_update_button)
        update_button_layout.addStretch()
        features_layout.addLayout(update_button_layout)

        features_group.setLayout(features_layout)
        main_layout.addWidget(features_group)

        # Storage group: surfaces the paths a user would typically need to
        # share when filing a bug report (log file, crash reports directory,
        # config file). Each row has a Copy button so the user can paste
        # the path straight into a GitHub issue without hunting for it.
        # Replaces the old "Version Information" group, which duplicated
        # content that now lives on the About tab.
        storage_group = QGroupBox(tr("settings_storage"))
        storage_layout = QVBoxLayout()

        for label_key, path_value in (
            (tr("label_log_file_path"), str(LOG_PATH)),
            (tr("label_crash_dir_path"), str(get_crash_dir())),
            (tr("label_config_file_path"), str(CONFIG_PATH)),
        ):
            row = QHBoxLayout()
            label = QLabel(label_key)
            label.setMinimumWidth(180)
            path_field = QLineEdit(path_value)
            path_field.setReadOnly(True)
            copy_button = QPushButton(tr("button_copy"))
            copy_button.setToolTip(tr("tooltip_copy_path"))
            copy_button.setProperty("buttonStyle", "secondary")
            copy_button.clicked.connect(
                lambda _checked=False, p=path_value: self._copy_path(p)
            )
            row.addWidget(label)
            row.addWidget(path_field)
            row.addWidget(copy_button)
            storage_layout.addLayout(row)

        storage_group.setLayout(storage_layout)
        main_layout.addWidget(storage_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.reset_button = QPushButton(tr("button_reset_defaults"))
        self.reset_button.setMinimumWidth(140)
        self.reset_button.clicked.connect(self._reset_defaults)
        button_layout.addWidget(self.reset_button)

        # Save button uses the default QPushButton style (primary blue
        # already defined in theme.py); the inline stylesheet here was a
        # straight duplicate that the theme manager could not override
        # when switching to light mode.
        self.save_button = QPushButton(tr("button_save_settings"))
        self.save_button.setMinimumWidth(140)
        self.save_button.clicked.connect(self._save_settings)
        button_layout.addWidget(self.save_button)

        main_layout.addLayout(button_layout)

        # Add stretch at bottom
        main_layout.addStretch()

    def _load_settings(self) -> None:
        """Load current settings from config."""
        config = self.config_manager.get_config()
        self.output_input.setText(config.output_directory)
        self.quality_combo.setCurrentText(config.default_quality)
        self.auto_update_checkbox.setChecked(config.check_updates_on_startup)
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
        default_quality = self.quality_combo.currentText()

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

        # Save language preference
        if language_changed:
            # Save to a config file or settings
            import json
            from pathlib import Path

            config_dir = Path.home() / ".yt-dlp-studio"
            config_dir.mkdir(exist_ok=True)
            language_file = config_dir / "language.json"

            try:
                with open(language_file, "w", encoding="utf-8") as f:
                    json.dump({"language": selected_lang_code}, f)
                logger.info(f"Language preference saved: {selected_lang_code}")
            except Exception as e:
                logger.error(f"Failed to save language preference: {e}")

        # Save other settings
        old_output_dir = self.config_manager.get_config().output_directory
        success = self.config_manager.update_config(
            output_directory=output_dir,
            default_quality=default_quality,
            check_updates_on_startup=self.auto_update_checkbox.isChecked(),
        )

        if success:
            logger.info("Settings saved successfully")

            # Emit signal if folder changed (v1.9.0 smart folder logic)
            if output_dir != old_output_dir:
                self.default_folder_changed.emit(output_dir)
                logger.info(f"Default folder changed signal emitted: {output_dir}")

            if language_changed:
                # Show restart required message
                QMessageBox.information(
                    self,
                    tr("dialog_settings_saved_restart_required"),
                    tr("msg_language_changed_restart_required", language=self.language_combo.currentText()),
                )
            else:
                QMessageBox.information(self, tr("dialog_settings_saved"), tr("msg_settings_saved"))
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
            logger.info("Settings reset to defaults")
            QMessageBox.information(self, tr("dialog_settings_reset"), tr("msg_all_settings_reset"))

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
                QMessageBox.warning(
                    self, tr("dialog_update_check_failed"), tr("msg_update_check_rate_limited")
                )
            else:
                QMessageBox.warning(
                    self, tr("dialog_update_check_failed"), tr("msg_update_check_failed", error=result.error)
                )
            return

        self.config_manager.update_config(last_update_check=datetime.now(timezone.utc).isoformat())

        if result.update_available and result.release_info:
            logger.info(f"Update available: {result.release_info['version']}")
            dialog = UpdateDialog(result.release_info, self, self.config_manager)
            dialog.exec()
        else:
            logger.info("No updates available")
            QMessageBox.information(
                self, tr("dialog_no_updates"), tr("msg_already_latest_version", version=APP_VERSION)
            )

    def _toggle_theme(self) -> None:
        """Toggle between dark and light themes (v2.0.0 - moved from menu bar)."""
        from ..ui.theme import ThemeMode, get_theme_manager

        theme_manager = get_theme_manager()
        stylesheet = theme_manager.toggle_theme()

        # Apply to main window
        main_window = self.window()
        if main_window:
            main_window.setStyleSheet(stylesheet)

        current_mode = theme_manager.get_current_mode()
        theme_name = tr("theme_dark") if current_mode == ThemeMode.DARK else tr("theme_light")

        QMessageBox.information(self, tr("dialog_theme_switched"), tr("msg_theme_switched", theme=theme_name))
        logger.info(f"Theme toggled to: {theme_name}")

    def _copy_path(self, path: str) -> None:
        """Copy a path to the clipboard and show a brief confirmation."""
        clipboard = QApplication.clipboard()
        if clipboard is None:
            return
        clipboard.setText(path)
        logger.debug(f"Copied path to clipboard: {path}")
        # Lightweight feedback - we use the status-bar style hint message so
        # the user gets confirmation without blocking the workflow.
        QMessageBox.information(self, tr("button_copy"), tr("msg_path_copied"))
