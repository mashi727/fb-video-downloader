"""
Tests for data models
"""

import pytest
from fb_downloader.core.models import VideoInfo, VideoQuality, DownloadConfig


class TestVideoInfo:
    def test_video_info_creation(self):
        video_info = VideoInfo(
            url="https://example.com/video.mp4",
            quality=VideoQuality.HD,
            size=1024000,
            title="Test Video",
            uploader="Test User",
            description="Test Description",
            video_id="123456",
        )

        assert video_info.url == "https://example.com/video.mp4"
        assert video_info.quality == VideoQuality.HD
        assert video_info.size == 1024000
        assert video_info.title == "Test Video"
        assert video_info.uploader == "Test User"
        assert video_info.description == "Test Description"
        assert video_info.video_id == "123456"

    def test_video_info_optional_fields(self):
        video_info = VideoInfo(url="https://example.com/video.mp4", quality=VideoQuality.SD)

        assert video_info.url == "https://example.com/video.mp4"
        assert video_info.quality == VideoQuality.SD
        assert video_info.size is None
        assert video_info.title is None
        assert video_info.uploader is None
        assert video_info.description is None
        assert video_info.video_id is None


class TestVideoQuality:
    def test_video_quality_values(self):
        assert VideoQuality.HD.value == "HD"
        assert VideoQuality.SD.value == "SD"
        assert VideoQuality.STANDARD.value == "標準"
        assert VideoQuality.UNKNOWN.value == "不明"


class TestDownloadConfig:
    def test_default_config(self):
        config = DownloadConfig()

        assert config.chunk_size == 8192
        assert config.timeout == 30
        assert config.max_retries == 3
        assert "User-Agent" in config.headers
        assert "Mozilla" in config.headers["User-Agent"]

    def test_custom_config(self):
        custom_headers = {"Custom-Header": "Value"}
        config = DownloadConfig(chunk_size=16384, timeout=60, max_retries=5, headers=custom_headers)

        assert config.chunk_size == 16384
        assert config.timeout == 60
        assert config.max_retries == 5
        assert config.headers == custom_headers

    def test_empty_headers_initialization(self):
        config = DownloadConfig(headers={})

        assert "User-Agent" in config.headers
        assert "Mozilla" in config.headers["User-Agent"]
