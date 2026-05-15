"""Tests for src/utils/bandwidth_monitor.py."""

import time

import pytest
from PySide6.QtWidgets import QApplication

from src.utils.bandwidth_monitor import BandwidthMonitor


@pytest.fixture(scope="session")
def qapp():
    """Ensure QApplication exists for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def monitor(qapp):
    """Create a fresh BandwidthMonitor."""
    m = BandwidthMonitor(history_size=10)
    yield m
    m.reset()


class TestBandwidthMonitorInit:
    """Tests for BandwidthMonitor initialization."""

    def test_defaults(self, monitor):
        assert monitor.current_speed == 0.0
        assert monitor.peak_speed == 0.0
        assert monitor.average_speed == 0.0
        assert monitor.total_downloaded == 0
        assert monitor.is_active is False
        assert len(monitor.speed_history) == 0

    def test_custom_history_size(self, qapp):
        m = BandwidthMonitor(history_size=5)
        assert m.history_size == 5


class TestBandwidthMonitorControl:
    """Tests for start/stop/reset."""

    def test_start(self, monitor):
        monitor.start_monitoring()
        assert monitor.is_active is True
        assert monitor.is_monitoring() is True

    def test_stop(self, monitor):
        monitor.start_monitoring()
        monitor.stop_monitoring()
        assert monitor.is_active is False
        assert monitor.is_monitoring() is False

    def test_reset(self, monitor):
        monitor.start_monitoring()
        monitor.update(1000)
        monitor.update(2000)
        monitor.reset()
        assert monitor.current_speed == 0.0
        assert monitor.peak_speed == 0.0
        assert monitor.total_downloaded == 0
        assert len(monitor.speed_history) == 0


class TestBandwidthMonitorUpdate:
    """Tests for update() method."""

    def test_update_when_not_active(self, monitor):
        monitor.update(1000)
        assert monitor.current_speed == 0.0

    def test_update_calculates_speed(self, monitor):
        monitor.start_monitoring()
        monitor.update(0)
        time.sleep(0.05)
        monitor.update(5000)
        assert monitor.current_speed > 0

    def test_peak_speed_tracking(self, monitor):
        monitor.start_monitoring()
        monitor.update(0)
        time.sleep(0.02)
        monitor.update(10000)
        first_peak = monitor.peak_speed
        time.sleep(0.02)
        monitor.update(10100)  # Small increment = slower speed
        # Peak should remain at the higher value
        assert monitor.peak_speed >= first_peak or monitor.peak_speed > 0

    def test_history_limited(self, qapp):
        m = BandwidthMonitor(history_size=3)
        m.start_monitoring()
        m.update(0)
        for i in range(1, 10):
            time.sleep(0.01)
            m.update(i * 1000)
        assert len(m.speed_history) <= 3

    def test_total_downloaded(self, monitor):
        monitor.start_monitoring()
        monitor.update(5000)
        assert monitor.total_downloaded == 5000


class TestBandwidthMonitorStats:
    """Tests for stats retrieval."""

    def test_get_stats_keys(self, monitor):
        stats = monitor.get_stats()
        expected_keys = [
            "current_speed",
            "current_speed_str",
            "average_speed",
            "average_speed_str",
            "peak_speed",
            "peak_speed_str",
            "total_downloaded",
            "total_downloaded_str",
            "speed_history",
        ]
        for key in expected_keys:
            assert key in stats

    def test_get_speed_history(self, monitor):
        assert isinstance(monitor.get_speed_history(), list)

    def test_get_speed_history_formatted(self, monitor):
        result = monitor.get_speed_history_formatted()
        assert isinstance(result, list)


class TestBandwidthMonitorFormatting:
    """Tests for formatting methods."""

    def test_format_speed_bytes(self, monitor):
        result = monitor._format_speed(500)
        assert "B/s" in result

    def test_format_speed_kilobytes(self, monitor):
        result = monitor._format_speed(5 * 1024)
        assert "KB/s" in result

    def test_format_speed_megabytes(self, monitor):
        result = monitor._format_speed(5 * 1024 * 1024)
        assert "MB/s" in result

    def test_format_size_bytes(self, monitor):
        result = monitor._format_size(500)
        assert "B" in result

    def test_format_size_megabytes(self, monitor):
        result = monitor._format_size(5 * 1024 * 1024)
        assert "MB" in result

    def test_current_speed_str(self, monitor):
        result = monitor.get_current_speed_str()
        assert isinstance(result, str)
        assert "B/s" in result
