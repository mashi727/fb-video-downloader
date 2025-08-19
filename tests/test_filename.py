"""
Tests for filename generation
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from fb_downloader.utils.filename import FileNameGenerator
from fb_downloader.core.models import VideoInfo, VideoQuality


class TestFileNameGenerator:
    def test_generate_without_video_info(self):
        with patch("fb_downloader.utils.filename.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
            filename = FileNameGenerator.generate(None)
            assert filename == "fb_video_20240101_120000.mp4"

    def test_generate_with_video_id_only(self):
        video_info = VideoInfo(
            url="https://example.com/video.mp4", quality=VideoQuality.HD, video_id="1234567890"
        )
        with patch("fb_downloader.utils.filename.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.side_effect = ["20240101", "120000"]
            filename = FileNameGenerator.generate(video_info)
            assert "20240101" in filename
            assert "fb_video" in filename
            assert ".mp4" in filename

    def test_generate_with_title(self):
        video_info = VideoInfo(
            url="https://example.com/video.mp4", quality=VideoQuality.HD, title="Test Video Title"
        )
        with patch("fb_downloader.utils.filename.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20240101"
            # Mock claude -p not available
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError()
                filename = FileNameGenerator.generate(video_info)
                assert "20240101" in filename
                assert ".mp4" in filename

    def test_sanitize_filename(self):
        dangerous_text = 'file<>:"/\\|?*name.txt'
        sanitized = FileNameGenerator._sanitize_filename(dangerous_text)
        assert "<" not in sanitized
        assert ">" not in sanitized
        assert ":" not in sanitized
        assert '"' not in sanitized
        assert "/" not in sanitized
        assert "\\" not in sanitized
        assert "|" not in sanitized
        assert "?" not in sanitized
        assert "*" not in sanitized
        assert "." not in sanitized  # Dots should also be removed except in extension

    def test_sanitize_filename_spaces(self):
        text = "file   name    with     spaces"
        sanitized = FileNameGenerator._sanitize_filename(text)
        assert sanitized == "file_name_with_spaces"

    def test_sanitize_filename_empty(self):
        assert FileNameGenerator._sanitize_filename("") == ""
        assert FileNameGenerator._sanitize_filename("   ") == ""
        assert FileNameGenerator._sanitize_filename("...") == ""
    
    def test_sanitize_filename_allowed_symbols(self):
        # Test that only - and _ are allowed as symbols
        text = "test-file_name"
        sanitized = FileNameGenerator._sanitize_filename(text)
        assert sanitized == "test-file_name"
        
        # Test other symbols are removed
        text = "test@file#name$test%file^name&test"
        sanitized = FileNameGenerator._sanitize_filename(text)
        assert "@" not in sanitized
        assert "#" not in sanitized
        assert "$" not in sanitized
        assert "%" not in sanitized
        assert "^" not in sanitized
        assert "&" not in sanitized
        
    def test_sanitize_filename_japanese_symbols(self):
        # Test Japanese punctuation is handled correctly
        text = "テスト・ファイル：名前！質問？"
        sanitized = FileNameGenerator._sanitize_filename(text)
        assert "・" not in sanitized  # Japanese middle dot
        assert "：" not in sanitized  # Full-width colon
        assert "！" not in sanitized  # Full-width exclamation
        assert "？" not in sanitized  # Full-width question mark
        
        # Test full-width hyphen is converted
        text = "テスト－ファイル"
        sanitized = FileNameGenerator._sanitize_filename(text)
        assert "－" not in sanitized  # Full-width hyphen should be converted
        assert "-" in sanitized or "_" in sanitized  # Should have half-width

    def test_summarize_text_english(self):
        text = "This is a very long title that needs to be summarized for the filename"
        summary = FileNameGenerator._summarize_text(text, target_length=30)
        assert len(summary) <= 30
        assert "_" not in summary or summary.count("_") < text.count(" ")

    def test_summarize_text_japanese(self):
        text = "これは非常に長い日本語のタイトルでファイル名用に要約する必要があります"
        summary = FileNameGenerator._summarize_text(text, target_length=20)
        assert len(summary) <= 20
        # Should not end with particles
        assert not summary.endswith(("を", "に", "が", "の", "で", "と", "は", "も"))

    def test_generate_with_long_title(self):
        long_title = "a" * 200
        video_info = VideoInfo(
            url="https://example.com/video.mp4",
            quality=VideoQuality.HD,
            title=long_title,
            video_id="123456789",
        )
        with patch("fb_downloader.utils.filename.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.side_effect = ["20240101", "1200"]
            filename = FileNameGenerator.generate(video_info)
            # Filename should be truncated to MAX_FILENAME_LENGTH + extension
            assert (
                len(filename) <= FileNameGenerator.MAX_FILENAME_LENGTH + 10 + 4
            )  # +10 for suffix, +4 for .mp4
            assert filename.endswith(".mp4")

    @patch("subprocess.run")
    def test_summarize_with_claude_success(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "素晴らしい_ビデオ_タイトル"
        mock_run.return_value = mock_result

        result = FileNameGenerator._summarize_with_claude("Long video title", max_length=50)
        assert result == "素晴らしい_ビデオ_タイトル"
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_summarize_with_claude_failure(self, mock_run):
        mock_run.side_effect = FileNotFoundError()
        result = FileNameGenerator._summarize_with_claude("Test text", max_length=50)
        assert result is None
