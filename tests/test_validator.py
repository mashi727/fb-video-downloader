"""
Tests for URL validator
"""

import pytest
from fb_downloader.utils.validator import URLValidator
from fb_downloader.core.exceptions import ValidationError


class TestURLValidator:
    def test_clean_url_basic(self):
        url = "https://www.facebook.com/watch/?v=123456789"
        cleaned = URLValidator.clean_url(url)
        assert cleaned == "https://www.facebook.com/watch/?v=123456789"

    def test_clean_url_with_backslashes(self):
        url = "https:\\/\\/www.facebook.com\\/watch\\/?v=123456789"
        cleaned = URLValidator.clean_url(url)
        assert cleaned == "https://www.facebook.com/watch/?v=123456789"

    def test_clean_url_with_duplicate_slashes(self):
        url = "https://www.facebook.com//watch////?v=123456789"
        cleaned = URLValidator.clean_url(url)
        assert cleaned == "https://www.facebook.com/watch/?v=123456789"

    def test_clean_url_trailing_slash(self):
        url = "https://www.facebook.com/watch/?v=123456789/"
        cleaned = URLValidator.clean_url(url)
        assert cleaned == "https://www.facebook.com/watch/?v=123456789"

    def test_clean_url_empty_raises_error(self):
        with pytest.raises(ValidationError):
            URLValidator.clean_url("")

    def test_validate_valid_facebook_url(self):
        urls = [
            "https://www.facebook.com/watch/?v=123456789",
            "https://fb.watch/abc123",
            "https://www.facebook.com/reel/123456789",
            "https://www.facebook.com/share/v/VIDEO_ID/",
        ]
        for url in urls:
            assert URLValidator.validate(url, interactive=False)

    def test_validate_invalid_url_format(self):
        invalid_urls = ["", "not-a-url", "ftp://www.facebook.com/video", "www.facebook.com/video"]
        for url in invalid_urls:
            assert not URLValidator.validate(url, interactive=False)

    def test_validate_non_facebook_url(self):
        url = "https://www.youtube.com/watch?v=123"
        # With interactive=False, should return False for non-Facebook URLs
        assert not URLValidator.validate(url, interactive=False)

    def test_extract_video_id_watch(self):
        url = "https://www.facebook.com/watch/?v=123456789"
        video_id, pattern = URLValidator.extract_video_id(url)
        assert video_id == "123456789"
        assert "/watch/" in pattern

    def test_extract_video_id_videos(self):
        url = "https://www.facebook.com/username/videos/987654321"
        video_id, pattern = URLValidator.extract_video_id(url)
        assert video_id == "987654321"
        assert "/videos/" in pattern

    def test_extract_video_id_reel(self):
        url = "https://www.facebook.com/reel/111222333"
        video_id, pattern = URLValidator.extract_video_id(url)
        assert video_id == "111222333"
        assert "/reel/" in pattern

    def test_extract_video_id_share(self):
        url = "https://www.facebook.com/share/v/ABC123XYZ/"
        video_id, pattern = URLValidator.extract_video_id(url)
        assert video_id == "ABC123XYZ"
        assert "/share/v/" in pattern

    def test_extract_video_id_not_found(self):
        url = "https://www.facebook.com/page/about"
        video_id, pattern = URLValidator.extract_video_id(url)
        assert video_id == ""
        assert pattern == ""
