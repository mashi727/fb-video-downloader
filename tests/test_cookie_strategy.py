"""Tests for how cookie and impersonation attempts are ordered"""

from pathlib import Path

import pytest

from fb_downloader.core.models import DownloadConfig
from fb_downloader.downloaders.ytdlp import YtDlpDownloader

YOUTUBE = "https://youtu.be/HV8wwEnTQ1A"
FACEBOOK = "https://www.facebook.com/reel/1796311761793453"

# What Safari actually held: youtube.com cookies, none of them a login
LOGGED_OUT_YOUTUBE = {(".youtube.com", "VISITOR_INFO1_LIVE"), (".youtube.com", "PREF")}
LOGGED_IN_YOUTUBE = LOGGED_OUT_YOUTUBE | {(".youtube.com", "LOGIN_INFO")}
LOGGED_IN_FACEBOOK = {(".facebook.com", "c_user"), (".facebook.com", "xs")}


@pytest.fixture
def downloader(tmp_path):
    """A downloader that believes it already resolved cookies and impersonation"""
    d = YtDlpDownloader(DownloadConfig())
    d._cookies_resolved = True
    d._cookie_file = Path(tmp_path / "cookies.txt")
    d._available_browser = "safari"
    d._impersonate_resolved = True
    d._impersonate_target = object()
    return d


def _labels(downloader, url):
    return [downloader._describe_attempt(c, i) for c, i in downloader._build_attempts(url)]


class TestAttemptOrder:
    def test_youtube_without_a_session_tries_plain_first(self, downloader):
        """A stale visitor session makes public videos report 'Video unavailable'"""
        downloader._cookie_index = LOGGED_OUT_YOUTUBE

        assert _labels(downloader, YOUTUBE)[0] == "plain request"

    def test_cookies_stay_available_as_a_fallback(self, downloader):
        downloader._cookie_index = LOGGED_OUT_YOUTUBE

        assert "cookies" in _labels(downloader, YOUTUBE)

    def test_youtube_with_a_session_tries_cookies_first(self, downloader):
        downloader._cookie_index = LOGGED_IN_YOUTUBE

        assert _labels(downloader, YOUTUBE)[0] == "cookies"

    def test_facebook_with_a_session_is_unchanged(self, downloader):
        downloader._cookie_index = LOGGED_IN_FACEBOOK

        assert _labels(downloader, FACEBOOK)[0] == "cookies + TLS impersonation"

    def test_unknown_site_keeps_cookies_first(self, downloader):
        downloader._cookie_index = LOGGED_OUT_YOUTUBE

        assert _labels(downloader, "https://example.com/video/1")[0] == "cookies"


class TestSessionDetection:
    def test_a_google_login_is_not_a_youtube_session(self, downloader):
        """SID on google.com must not be read as being signed in to YouTube"""
        downloader._cookie_index = {(".google.com", "SID")}

        assert not downloader._cookies_carry_session(YOUTUBE)

    def test_youtube_login_cookie_counts(self, downloader):
        downloader._cookie_index = {(".youtube.com", "SID")}

        assert downloader._cookies_carry_session(YOUTUBE)
