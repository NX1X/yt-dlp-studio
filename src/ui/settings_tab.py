"""
Settings tab UI for YT-DLP Studio.

Provides interface for configuring application settings.
"""

import subprocess
import sys

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ..backend.config_manager import ConfigManager
from ..backend.format_handler import FormatHandler
from ..backend.yt_dlp_wrapper import YtDlpWrapper
from ..utils.constants import APP_NAME, APP_VERSION
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

        # Theme toggle button
        theme_button_layout = QHBoxLayout()
        theme_label = QLabel(tr("label_theme"))
        theme_label.setMinimumWidth(180)
        self.toggle_theme_button = QPushButton(tr("button_toggle_theme"))
        self.toggle_theme_button.setMinimumWidth(180)
        self.toggle_theme_button.setToolTip(tr("tooltip_toggle_theme"))
        self.toggle_theme_button.clicked.connect(self._toggle_theme)
        self.toggle_theme_button.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
        """)
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

        # Check for updates button (v1.8.0 - clean, professional)
        update_button_layout = QHBoxLayout()
        self.check_update_button = QPushButton(tr("button_check_update"))
        self.check_update_button.setMinimumWidth(180)
        self.check_update_button.clicked.connect(self._check_for_updates)
        self.check_update_button.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
        """)
        update_button_layout.addWidget(self.check_update_button)
        update_button_layout.addStretch()
        features_layout.addLayout(update_button_layout)

        features_group.setLayout(features_layout)
        main_layout.addWidget(features_group)

        # v0.8.0: Version Information (credits moved to About tab)
        version_group = QGroupBox(tr("settings_version_info"))
        version_layout = QVBoxLayout()

        # Get version information
        try:
            ytdlp_version = YtDlpWrapper.get_ytdlp_version()
        except:
            ytdlp_version = "Unknown"

        try:
            # Get FFmpeg version
            ffmpeg_version = self._get_ffmpeg_version()
        except:
            ffmpeg_version = "Not Found"

        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        try:
            from PySide6 import __version__ as pyside_version
        except:
            pyside_version = "Unknown"

        # Create version info text (technical details only)
        version_info = f"""<b>{APP_NAME} v{APP_VERSION}</b><br>
<span style="color: #888; font-size: 10pt;">Part of NXTools by NX1X</span><br><br>

<b>Core Components:</b><br>
<table style="color: #ccc; border-spacing: 0;">
<tr><td style="padding: 4px 8px;"><b>yt-dlp:</b></td><td style="padding: 4px;">v{ytdlp_version}</td></tr>
<tr><td style="padding: 4px 8px;"><b>FFmpeg:</b></td><td style="padding: 4px;">{ffmpeg_version}</td></tr>
<tr><td style="padding: 4px 8px;"><b>Python:</b></td><td style="padding: 4px;">v{python_version}</td></tr>
<tr><td style="padding: 4px 8px;"><b>PySide6 (Qt):</b></td><td style="padding: 4px;">v{pyside_version}</td></tr>
</table><br>

<p style="color: #888; font-size: 10pt;">
For detailed credits and acknowledgments, see the <b>About</b> tab.
</p>
"""

        version_text = QTextBrowser()
        version_text.setReadOnly(True)
        version_text.setHtml(version_info)
        version_text.setMinimumHeight(200)
        version_text.setMaximumHeight(250)
        version_text.setOpenExternalLinks(True)
        version_layout.addWidget(version_text)

        version_group.setLayout(version_layout)
        main_layout.addWidget(version_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.reset_button = QPushButton(tr("button_reset_defaults"))
        self.reset_button.setMinimumWidth(140)
        self.reset_button.clicked.connect(self._reset_defaults)
        button_layout.addWidget(self.reset_button)

        self.save_button = QPushButton(tr("button_save_settings"))
        self.save_button.setMinimumWidth(140)
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
        """)
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
        success = self.config_manager.update_config(output_directory=output_dir, default_quality=default_quality)

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
        """Check for application updates (v1.7.0)."""
        from ..backend.update_checker import UpdateChecker
        from ..ui.update_dialog import UpdateDialog

        self.check_update_button.setEnabled(False)
        self.check_update_button.setText(tr("button_checking"))

        try:
            checker = UpdateChecker()
            update_available, release_info = checker.check_for_updates()

            if update_available and release_info:
                logger.info(f"Update available: {release_info['version']}")
                # Show update dialog
                dialog = UpdateDialog(release_info, self)
                dialog.exec()
            else:
                logger.info("No updates available")
                QMessageBox.information(
                    self, tr("dialog_no_updates"), tr("msg_already_latest_version", version=APP_VERSION)
                )

        except Exception as e:
            logger.error(f"Update check failed: {e}")
            QMessageBox.warning(self, tr("dialog_update_check_failed"), tr("msg_update_check_failed", error=str(e)))
        finally:
            self.check_update_button.setEnabled(True)
            self.check_update_button.setText(tr("button_check_for_updates_now"))

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

    def _get_ffmpeg_version(self) -> str:
        """Get FFmpeg version string."""
        try:
            # Try to run ffmpeg -version
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # Extract version from first line
                first_line = result.stdout.split("\n")[0]
                # Example: "ffmpeg version 2024-11-27-git-..."
                if "version" in first_line:
                    parts = first_line.split()
                    if len(parts) >= 3:
                        return parts[2]  # The version number
            return "Installed (version unknown)"
        except FileNotFoundError:
            return "Not Found in PATH"
        except Exception as e:
            logger.error(f"Error getting FFmpeg version: {e}")
            return "Error detecting version"
