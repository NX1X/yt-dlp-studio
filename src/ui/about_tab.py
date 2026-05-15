"""
About tab for YT-DLP Studio.

Displays application information, credits, and keyboard shortcuts.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QScrollArea, QTextBrowser, QVBoxLayout, QWidget

from ..utils.constants import APP_DESCRIPTION, APP_NAME, APP_VERSION
from ..utils.logger import get_logger
from ..utils.translations import tr

logger = get_logger()


class AboutTab(QWidget):
    """About tab displaying application information."""

    def __init__(self):
        """Initialize the About tab."""
        super().__init__()
        self._setup_ui()
        logger.debug("AboutTab initialized")

    def _setup_ui(self):
        """Set up the About tab UI."""
        # Create scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        # Main content widget
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Application Title
        title_label = QLabel(f"{APP_NAME}")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Version
        version_label = QLabel(f"{tr('label_current_version')} {APP_VERSION}")
        version_font = QFont()
        version_font.setPointSize(12)
        version_label.setFont(version_font)
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("color: #888;")
        layout.addWidget(version_label)

        layout.addSpacing(10)

        # Description
        desc_label = QLabel(APP_DESCRIPTION)
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet("color: #aaa; font-size: 11pt;")
        layout.addWidget(desc_label)

        layout.addSpacing(20)

        # Details Group (v3.0.0 - simplified)
        details_group = QGroupBox("Details")
        details_layout = QVBoxLayout()

        details_text = QTextBrowser()
        details_text.setOpenExternalLinks(False)
        details_text.setMaximumHeight(100)
        details_text.setHtml(f"""
        <div style="color: #ccc;">
        <p><b>{APP_NAME}</b> is a user-friendly graphical interface for yt-dlp,
        making it easy to download videos from YouTube.</p>
        <p style="color: #888; font-size: 10pt;">
        For detailed version information and technical details, see the Settings tab.</p>
        </div>
        """)
        details_layout.addWidget(details_text)

        details_group.setLayout(details_layout)
        layout.addWidget(details_group)

        # About the Developer Group (v3.0.0 - renamed from NXtools Info)
        developer_group = QGroupBox("About the Developer")
        nxtools_layout = QVBoxLayout()

        nxtools_text = QTextBrowser()
        nxtools_text.setOpenExternalLinks(True)
        nxtools_text.setMaximumHeight(120)
        nxtools_text.setHtml("""
        <p style="color: #ccc;">
        This tool is part of <b>NXtools</b> - a collection of productivity tools.<br><br>
        <b>Website:</b> <a href="https://nx1xlab.dev/nxtools" style="color: #58a6ff;">https://nx1xlab.dev/nxtools</a><br><br>
        <b>Support Development:</b><br>
        If you find this tool useful, consider buying me a coffee!<br>
        <a href="https://buymeacoffee.com/nx1x" style="color: #58a6ff;">Buy Me a Coffee</a>
        </p>
        """)
        nxtools_layout.addWidget(nxtools_text)

        developer_group.setLayout(nxtools_layout)
        layout.addWidget(developer_group)

        # Credits Group
        credits_group = QGroupBox(tr("label_credits"))
        credits_layout = QVBoxLayout()

        credits_text = QTextBrowser()
        credits_text.setOpenExternalLinks(True)
        credits_text.setMaximumHeight(450)

        # Get Python version
        import sys

        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        credits_text.setHtml(f"""
        <div style="color: #ccc;">
        <p>{tr('text_credits_description')}</p>

        <h3 style="color: #58a6ff; margin-top: 15px;">Core Dependencies</h3>

        <p><b>yt-dlp</b> - Video downloader engine<br>
        <span style="color: #888; font-size: 10pt;">Video/audio downloader engine</span><br>
        License: Unlicense<br>
        <a href="https://github.com/yt-dlp/yt-dlp" style="color: #58a6ff;">https://github.com/yt-dlp/yt-dlp</a></p>

        <p><b>FFmpeg</b> - Multimedia processing framework<br>
        <span style="color: #888; font-size: 10pt;">Handles video/audio conversion, merging, and post-processing</span><br>
        License: LGPL 2.1+ / GPL 2+<br>
        <a href="https://ffmpeg.org/" style="color: #58a6ff;">https://ffmpeg.org/</a></p>

        <h3 style="color: #58a6ff; margin-top: 15px;">Development Framework</h3>

        <p><b>Python {python_version}</b> - Programming language<br>
        <span style="color: #888; font-size: 10pt;">Application runtime environment</span><br>
        License: PSF License<br>
        <a href="https://www.python.org/" style="color: #58a6ff;">https://www.python.org/</a></p>

        <p><b>PySide6 (Qt6)</b> - GUI framework<br>
        <span style="color: #888; font-size: 10pt;">Cross-platform user interface and application framework</span><br>
        License: LGPL<br>
        <a href="https://www.qt.io/qt-for-python" style="color: #58a6ff;">https://www.qt.io/qt-for-python</a></p>

        <h3 style="color: #58a6ff; margin-top: 15px;">Build & Distribution</h3>

        <p><b>PyInstaller</b> - Executable bundler<br>
        <span style="color: #888; font-size: 10pt;">Packages Python applications into standalone executables</span><br>
        License: GPL<br>
        <a href="https://pyinstaller.org/" style="color: #58a6ff;">https://pyinstaller.org/</a></p>

        <p><b>UPX</b> - Executable compressor<br>
        <span style="color: #888; font-size: 10pt;">Reduces executable file size</span><br>
        License: GPL<br>
        <a href="https://upx.github.io/" style="color: #58a6ff;">https://upx.github.io/</a></p>

        <p style="margin-top: 20px; padding: 10px; background-color: #1a1a1a; border-left: 3px solid #58a6ff;">
        <b>Thank you</b> to all the developers and contributors of these amazing open source projects!
        This application would not be possible without your dedication and hard work. ❤️
        </p>
        </div>
        """)
        credits_layout.addWidget(credits_text)

        credits_group.setLayout(credits_layout)
        layout.addWidget(credits_group)

        # Keyboard Shortcuts Group
        shortcuts_group = QGroupBox(tr("shortcuts_title"))
        shortcuts_layout = QVBoxLayout()

        shortcuts_text = QTextBrowser()
        shortcuts_text.setOpenExternalLinks(False)
        shortcuts_text.setMaximumHeight(300)
        shortcuts_text.setHtml(f"""
        <h3>{tr('shortcuts_general')}</h3>
        <table style="color: #ccc; width: 100%;">
        <tr><td style="padding: 4px;"><b>Ctrl+Q</b></td><td style="padding: 4px;">{tr('shortcut_quit_app')}</td></tr>
        <tr><td style="padding: 4px;"><b>F1</b></td><td style="padding: 4px;">{tr('shortcut_show_help')}</td></tr>
        <tr><td style="padding: 4px;"><b>Esc</b></td><td style="padding: 4px;">{tr('shortcut_close_dialogs')}</td></tr>
        </table>

        <h3>{tr('shortcuts_download_tab')}</h3>
        <table style="color: #ccc; width: 100%;">
        <tr><td style="padding: 4px;"><b>Ctrl+V</b></td><td style="padding: 4px;">{tr('shortcut_paste_url')}</td></tr>
        <tr><td style="padding: 4px;"><b>Enter</b></td><td style="padding: 4px;">{tr('shortcut_start_download')}</td></tr>
        <tr><td style="padding: 4px;"><b>Ctrl+Shift+I</b></td><td style="padding: 4px;">{tr('shortcut_show_video_info')}</td></tr>
        <tr><td style="padding: 4px;"><b>Ctrl+D</b></td><td style="padding: 4px;">{tr('shortcut_download_now')}</td></tr>
        <tr><td style="padding: 4px;"><b>Ctrl+Shift+Q</b></td><td style="padding: 4px;">{tr('shortcut_add_to_queue')}</td></tr>
        </table>

        <h3>{tr('shortcuts_queue_tab')}</h3>
        <table style="color: #ccc; width: 100%;">
        <tr><td style="padding: 4px;"><b>Delete</b></td><td style="padding: 4px;">{tr('shortcut_remove_task')}</td></tr>
        <tr><td style="padding: 4px;"><b>Ctrl+Up</b></td><td style="padding: 4px;">{tr('shortcut_move_task_up')}</td></tr>
        <tr><td style="padding: 4px;"><b>Ctrl+Down</b></td><td style="padding: 4px;">{tr('shortcut_move_task_down')}</td></tr>
        </table>
        """)
        shortcuts_layout.addWidget(shortcuts_text)

        shortcuts_group.setLayout(shortcuts_layout)
        layout.addWidget(shortcuts_group)

        # Links
        links_layout = QHBoxLayout()
        links_layout.addStretch()

        # GitHub button (placeholder - add when repo is public)
        # github_btn = QPushButton(tr('button_view_on_github'))
        # github_btn.clicked.connect(self._open_github)
        # links_layout.addWidget(github_btn)

        # Documentation button (placeholder)
        # docs_btn = QPushButton(tr('button_documentation'))
        # docs_btn.clicked.connect(self._open_docs)
        # links_layout.addWidget(docs_btn)

        links_layout.addStretch()
        layout.addLayout(links_layout)

        layout.addStretch()

        # Set scroll area content
        scroll.setWidget(content_widget)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

        self.setLayout(main_layout)

    def _open_github(self):
        """Open GitHub repository in browser."""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl("https://github.com/NX1X/yt-dlp-studio"))
        logger.debug("Opened GitHub repository")

    def _open_docs(self):
        """Open documentation in browser."""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl("https://your-docs-url.com"))
        logger.debug("Opened documentation")
