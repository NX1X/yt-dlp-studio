"""
Bandwidth Widget for YT-DLP Studio.

Displays real-time bandwidth statistics and speed graph.
"""

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QFrame, QGroupBox, QLabel, QVBoxLayout, QWidget

from ..utils.bandwidth_monitor import BandwidthMonitor
from ..utils.logger import get_logger
from ..utils.translations import tr

logger = get_logger()


class SpeedGraphWidget(QWidget):
    """
    Widget for displaying speed graph.

    Shows download speed over time as a line graph.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.speed_history = []
        self.max_speed = 1.0  # Minimum 1 byte to avoid division by zero
        self.setMinimumHeight(150)
        logger.debug("SpeedGraphWidget initialized")

    def set_speed_history(self, history: list[float]):
        """
        Update speed history for graphing.

        Args:
            history: List of speed values
        """
        self.speed_history = history

        # Update max speed for scaling
        if history:
            max_in_history = max(history)
            self.max_speed = max(max_in_history, 1.0)

        self.update()  # Trigger repaint

    def paintEvent(self, event):
        """Paint the speed graph."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Get widget dimensions
        width = self.width()
        height = self.height()
        margin = 10

        # Background
        painter.fillRect(0, 0, width, height, QColor("#2b2b2b"))

        # Grid lines
        grid_pen = QPen(QColor("#3c3c3c"), 1)
        painter.setPen(grid_pen)

        # Horizontal grid lines
        for i in range(5):
            y = margin + (height - 2 * margin) * i / 4
            painter.drawLine(margin, int(y), width - margin, int(y))

        # Vertical grid lines
        for i in range(10):
            x = margin + (width - 2 * margin) * i / 9
            painter.drawLine(int(x), margin, int(x), height - margin)

        # Draw speed line
        if len(self.speed_history) > 1:
            line_pen = QPen(QColor("#00ff00"), 2)
            painter.setPen(line_pen)

            points = []
            for i, speed in enumerate(self.speed_history):
                # Calculate position
                x = margin + (width - 2 * margin) * i / max(len(self.speed_history) - 1, 1)
                y = height - margin - (height - 2 * margin) * (speed / self.max_speed)
                points.append(QPointF(x, y))

            # Draw line segments
            for i in range(len(points) - 1):
                painter.drawLine(points[i], points[i + 1])

        # Draw labels
        painter.setPen(QColor("#ffffff"))
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)

        # Max speed label
        max_speed_str = self._format_speed(self.max_speed)
        painter.drawText(5, 15, f"Max: {max_speed_str}")

        # Zero speed label
        painter.drawText(5, height - 5, "0 B/s")

    def _format_speed(self, bytes_per_sec: float) -> str:
        """Format speed for display."""
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec:.0f} B/s"
        elif bytes_per_sec < 1024 * 1024:
            return f"{bytes_per_sec / 1024:.1f} KB/s"
        elif bytes_per_sec < 1024 * 1024 * 1024:
            return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"
        else:
            return f"{bytes_per_sec / (1024 * 1024 * 1024):.2f} GB/s"


class BandwidthWidget(QWidget):
    """
    Widget for displaying bandwidth statistics.

    Shows:
    - Current speed
    - Average speed
    - Peak speed
    - Total downloaded
    - Speed graph
    """

    def __init__(self, bandwidth_monitor: BandwidthMonitor = None, parent=None):
        """
        Initialize BandwidthWidget.

        Args:
            bandwidth_monitor: BandwidthMonitor instance (optional)
            parent: Parent widget
        """
        super().__init__(parent)
        self.bandwidth_monitor = bandwidth_monitor
        self._setup_ui()
        self._setup_update_timer()
        logger.debug("BandwidthWidget initialized")

    def _setup_ui(self):
        """Setup the widget UI."""
        layout = QVBoxLayout()

        # Title
        title_label = QLabel(f"<b>{tr('title_bandwidth_monitor')}</b>")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Statistics group
        stats_group = QGroupBox(tr("group_statistics"))
        stats_layout = QVBoxLayout()

        # Current speed
        self.current_speed_label = QLabel("Current Speed: 0 B/s")
        stats_layout.addWidget(self.current_speed_label)

        # Average speed
        self.average_speed_label = QLabel("Average Speed: 0 B/s")
        stats_layout.addWidget(self.average_speed_label)

        # Peak speed
        self.peak_speed_label = QLabel("Peak Speed: 0 B/s")
        stats_layout.addWidget(self.peak_speed_label)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        stats_layout.addWidget(separator)

        # Total downloaded
        self.total_downloaded_label = QLabel("Total Downloaded: 0 B")
        stats_layout.addWidget(self.total_downloaded_label)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # Speed graph
        graph_group = QGroupBox(tr("group_speed_graph"))
        graph_layout = QVBoxLayout()

        self.speed_graph = SpeedGraphWidget()
        graph_layout.addWidget(self.speed_graph)

        graph_group.setLayout(graph_layout)
        layout.addWidget(graph_group)

        self.setLayout(layout)

    def _setup_update_timer(self):
        """Setup timer for updating the display."""
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.start(1000)  # Update every second

    def _update_display(self):
        """Update the display with current statistics."""
        if not self.bandwidth_monitor or not self.bandwidth_monitor.is_monitoring():
            return

        # Get statistics
        stats = self.bandwidth_monitor.get_stats()

        # Update labels
        self.current_speed_label.setText(f"Current Speed: {stats['current_speed_str']}")
        self.average_speed_label.setText(f"Average Speed: {stats['average_speed_str']}")
        self.peak_speed_label.setText(f"Peak Speed: {stats['peak_speed_str']}")
        self.total_downloaded_label.setText(f"Total Downloaded: {stats['total_downloaded_str']}")

        # Update graph
        self.speed_graph.set_speed_history(stats["speed_history"])

    def set_bandwidth_monitor(self, monitor: BandwidthMonitor):
        """
        Set the bandwidth monitor.

        Args:
            monitor: BandwidthMonitor instance
        """
        self.bandwidth_monitor = monitor
        logger.debug("BandwidthMonitor set")

    def reset_display(self):
        """Reset the display to zero values."""
        self.current_speed_label.setText(f"{tr('bandwidth_current_speed')} 0 B/s")
        self.average_speed_label.setText(f"{tr('bandwidth_avg_speed')} 0 B/s")
        self.peak_speed_label.setText(f"{tr('bandwidth_peak_speed')} 0 B/s")
        self.total_downloaded_label.setText(f"{tr('bandwidth_total_downloaded')} 0 B")
        self.speed_graph.set_speed_history([])
        logger.debug("Display reset")

    def show_widget(self):
        """Show the widget and start updating."""
        self.show()
        if self.bandwidth_monitor:
            self.bandwidth_monitor.start_monitoring()
        logger.debug("Widget shown and monitoring started")

    def hide_widget(self):
        """Hide the widget and stop updating."""
        self.hide()
        if self.bandwidth_monitor:
            self.bandwidth_monitor.stop_monitoring()
        logger.debug("Widget hidden and monitoring stopped")
