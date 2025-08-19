"""
Tests for custom exceptions
"""

import pytest
from fb_downloader.core.exceptions import (
    DownloaderError,
    VideoNotFoundError,
    NetworkError,
    ExtractionError,
    ValidationError,
)


class TestExceptions:
    def test_downloader_error(self):
        error = DownloaderError("Base error")
        assert str(error) == "Base error"
        assert isinstance(error, Exception)

    def test_video_not_found_error_basic(self):
        error = VideoNotFoundError()
        assert "Video not found" in str(error)
        assert error.url == ""

    def test_video_not_found_error_with_url(self):
        url = "https://facebook.com/video/123"
        error = VideoNotFoundError("Custom message", url=url)
        assert "Custom message" in str(error)
        assert url in str(error)
        assert error.url == url

    def test_network_error_basic(self):
        error = NetworkError()
        assert "Network error occurred" in str(error)
        assert error.status_code == 0

    def test_network_error_with_status_code(self):
        error = NetworkError("Connection failed", status_code=404)
        assert "Connection failed" in str(error)
        assert "404" in str(error)
        assert error.status_code == 404

    def test_extraction_error(self):
        error = ExtractionError("Failed to extract video")
        assert str(error) == "Failed to extract video"
        assert isinstance(error, DownloaderError)

    def test_validation_error(self):
        error = ValidationError("Invalid URL format")
        assert str(error) == "Invalid URL format"
        assert isinstance(error, DownloaderError)

    def test_exception_hierarchy(self):
        assert issubclass(VideoNotFoundError, DownloaderError)
        assert issubclass(NetworkError, DownloaderError)
        assert issubclass(ExtractionError, DownloaderError)
        assert issubclass(ValidationError, DownloaderError)
        assert issubclass(DownloaderError, Exception)
