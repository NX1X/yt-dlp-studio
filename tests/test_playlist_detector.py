"""Tests for src/utils/playlist_detector.py."""

from src.utils.playlist_detector import PlaylistDetector


class TestIsPlaylistUrl:
    """Tests for PlaylistDetector.is_playlist_url()."""

    def test_youtube_playlist_with_list_param(self):
        url = "https://www.youtube.com/watch?v=abc&list=PLx123abc"
        is_playlist, platform = PlaylistDetector.is_playlist_url(url)
        assert is_playlist is True
        assert platform == "youtube"

    def test_youtube_playlist_path(self):
        url = "https://www.youtube.com/playlist?list=PLx123abc"
        is_playlist, platform = PlaylistDetector.is_playlist_url(url)
        assert is_playlist is True
        assert platform == "youtube"

    def test_youtube_channel_at_videos(self):
        url = "https://www.youtube.com/@channelname/videos"
        is_playlist, platform = PlaylistDetector.is_playlist_url(url)
        assert is_playlist is True
        assert platform == "youtube_channel"

    def test_youtube_channel_id_videos(self):
        url = "https://www.youtube.com/channel/UC123abc/videos"
        is_playlist, platform = PlaylistDetector.is_playlist_url(url)
        assert is_playlist is True
        assert platform == "youtube_channel"

    def test_vimeo_album(self):
        url = "https://vimeo.com/album/12345"
        is_playlist, platform = PlaylistDetector.is_playlist_url(url)
        assert is_playlist is True
        assert platform == "vimeo"

    def test_vimeo_channel(self):
        url = "https://vimeo.com/channels/staffpicks"
        is_playlist, platform = PlaylistDetector.is_playlist_url(url)
        assert is_playlist is True
        assert platform == "vimeo"

    def test_dailymotion_playlist(self):
        url = "https://www.dailymotion.com/playlist/x5nmbq"
        is_playlist, platform = PlaylistDetector.is_playlist_url(url)
        assert is_playlist is True
        assert platform == "dailymotion"

    def test_regular_youtube_video(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        is_playlist, platform = PlaylistDetector.is_playlist_url(url)
        assert is_playlist is False
        assert platform == "unknown"

    def test_regular_url(self):
        url = "https://example.com/video/123"
        is_playlist, platform = PlaylistDetector.is_playlist_url(url)
        assert is_playlist is False
        assert platform == "unknown"


class TestExtractPlaylistId:
    """Tests for PlaylistDetector.extract_playlist_id()."""

    def test_youtube_playlist_id(self):
        url = "https://www.youtube.com/playlist?list=PLx123abc_def"
        result = PlaylistDetector.extract_playlist_id(url, "youtube")
        assert result == "PLx123abc_def"

    def test_youtube_channel_at(self):
        url = "https://www.youtube.com/@mychannel/videos"
        result = PlaylistDetector.extract_playlist_id(url, "youtube_channel")
        assert result == "mychannel"

    def test_vimeo_album_id(self):
        url = "https://vimeo.com/album/12345"
        result = PlaylistDetector.extract_playlist_id(url, "vimeo")
        assert result == "12345"

    def test_vimeo_channel_name(self):
        url = "https://vimeo.com/channels/staffpicks"
        result = PlaylistDetector.extract_playlist_id(url, "vimeo")
        assert result == "staffpicks"

    def test_unknown_platform(self):
        result = PlaylistDetector.extract_playlist_id("https://example.com", "unknown")
        assert result == ""


class TestGetPlatformName:
    """Tests for PlaylistDetector.get_platform_name()."""

    def test_youtube(self):
        assert PlaylistDetector.get_platform_name("youtube") == "YouTube Playlist"

    def test_youtube_channel(self):
        assert PlaylistDetector.get_platform_name("youtube_channel") == "YouTube Channel"

    def test_vimeo(self):
        assert PlaylistDetector.get_platform_name("vimeo") == "Vimeo Album/Channel"

    def test_dailymotion(self):
        assert PlaylistDetector.get_platform_name("dailymotion") == "Dailymotion Playlist"

    def test_unknown(self):
        assert PlaylistDetector.get_platform_name("unknown") == "Unknown"

    def test_nonexistent(self):
        assert PlaylistDetector.get_platform_name("nonexistent") == "Unknown"
