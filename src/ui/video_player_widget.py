"""
Video Player Widget for YT-DLP Studio.

Provides built-in video preview/playback using PySide6 multimedia.
"""

import os
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QPushButton, QSlider, QStyle, QVBoxLayout, QWidget

from ..utils.logger import get_logger
from ..utils.translations import tr

logger = get_logger()


class VideoPlayerWidget(QWidget):
    """
    Video player widget with playback controls.

    Features:
    - Video playback
    - Play/Pause control
    - Seek slider
    - Volume control
    - Time display
    """

    def __init__(self, parent=None):
        """
        Initialize VideoPlayerWidget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.current_file = None
        self._setup_ui()
        self._setup_player()
        logger.debug("VideoPlayerWidget initialized")

    def _setup_ui(self):
        """Setup the widget UI."""
        layout = QVBoxLayout()

        # Video widget
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(300)
        layout.addWidget(self.video_widget)

        # Time labels
        time_layout = QHBoxLayout()
        self.time_label = QLabel("00:00")
        time_layout.addWidget(self.time_label)

        # Seek slider
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.sliderMoved.connect(self._on_seek)
        time_layout.addWidget(self.seek_slider)

        self.duration_label = QLabel("00:00")
        time_layout.addWidget(self.duration_label)

        layout.addLayout(time_layout)

        # Controls
        controls_layout = QHBoxLayout()

        # Play/Pause button
        self.play_button = QPushButton()
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.play_button.clicked.connect(self._toggle_playback)
        controls_layout.addWidget(self.play_button)

        # Stop button
        self.stop_button = QPushButton()
        self.stop_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.stop_button.clicked.connect(self._stop_playback)
        controls_layout.addWidget(self.stop_button)

        controls_layout.addStretch()

        # Volume label
        volume_label = QLabel(tr("label_volume"))
        controls_layout.addWidget(volume_label)

        # Volume slider
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setMaximumWidth(100)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        controls_layout.addWidget(self.volume_slider)

        # File label
        self.file_label = QLabel(tr("text_no_file_loaded"))
        self.file_label.setStyleSheet("color: gray;")

        layout.addLayout(controls_layout)
        layout.addWidget(self.file_label)

        self.setLayout(layout)

    def _setup_player(self):
        """Setup media player."""
        # Create player
        self.player = QMediaPlayer()

        # Create audio output
        self.audio_output = QAudioOutput()
        self.audio_output.setVolume(0.7)
        self.player.setAudioOutput(self.audio_output)

        # Set video output
        self.player.setVideoOutput(self.video_widget)

        # Connect signals
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_state_changed)
        self.player.errorOccurred.connect(self._on_error)

        logger.debug("Media player setup complete")

    def load_file(self, file_path: str):
        """
        Load a video file for playback.

        Args:
            file_path: Path to video file
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            QMessageBox.warning(
                self, tr("dialog_file_not_found"), tr("msg_file_not_found_details", file_path=file_path)
            )
            return

        self.current_file = file_path

        # Load file
        file_url = QUrl.fromLocalFile(file_path)
        self.player.setSource(file_url)

        # Update file label
        filename = Path(file_path).name
        self.file_label.setText(f"File: {filename}")

        logger.info(f"Loaded video file: {file_path}")

    def _toggle_playback(self):
        """Toggle play/pause."""
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _stop_playback(self):
        """Stop playback."""
        self.player.stop()

    def _on_seek(self, position):
        """
        Handle seek slider movement.

        Args:
            position: New position in milliseconds
        """
        self.player.setPosition(position)

    def _on_volume_changed(self, value):
        """
        Handle volume slider change.

        Args:
            value: New volume (0-100)
        """
        self.audio_output.setVolume(value / 100.0)

    def _on_position_changed(self, position):
        """
        Handle playback position change.

        Args:
            position: Current position in milliseconds
        """
        # Update slider
        self.seek_slider.setValue(position)

        # Update time label
        self.time_label.setText(self._format_time(position))

    def _on_duration_changed(self, duration):
        """
        Handle duration change.

        Args:
            duration: Total duration in milliseconds
        """
        self.seek_slider.setRange(0, duration)
        self.duration_label.setText(self._format_time(duration))

    def _on_state_changed(self, state):
        """
        Handle playback state change.

        Args:
            state: New playback state
        """
        if state == QMediaPlayer.PlayingState:
            self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

    def _on_error(self, error, error_string):
        """
        Handle player error.

        Args:
            error: Error code
            error_string: Error message
        """
        logger.error(f"Player error: {error_string}")
        QMessageBox.critical(self, tr("dialog_playback_error"), tr("msg_error_playing_video", error=error_string))

    def _format_time(self, milliseconds):
        """
        Format time for display.

        Args:
            milliseconds: Time in milliseconds

        Returns:
            Formatted time string (MM:SS)
        """
        seconds = milliseconds // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def clear(self):
        """Clear the player and reset UI."""
        self.player.stop()
        self.player.setSource(QUrl())
        self.current_file = None
        self.file_label.setText(tr("text_no_file_loaded"))
        self.time_label.setText("00:00")
        self.duration_label.setText("00:00")
        self.seek_slider.setRange(0, 0)
        logger.debug("Player cleared")

    def closeEvent(self, event):
        """Handle widget close."""
        self.player.stop()
        super().closeEvent(event)
