"""Tests for the description sidecar written next to each video"""

from fb_downloader.core.models import VideoInfo, VideoQuality
from fb_downloader.downloaders.base import BaseDownloader
from fb_downloader.tools.rename import _strip_leading_link


def _info(description=None, source_url=None):
    return VideoInfo(
        url="",
        quality=VideoQuality.STANDARD,
        description=description,
        source_url=source_url,
    )


class TestSaveDescription:
    def test_source_link_is_written_first(self, tmp_path):
        video = tmp_path / "20260920_焼きシーザーサラダ.mp4"
        url = "https://www.instagram.com/reel/DaE7MMqBaL8"

        BaseDownloader._save_description(video, _info("本文の1行目\n2行目", url))

        text = video.with_suffix(".txt").read_text(encoding="utf-8")
        assert text.splitlines()[0] == url
        assert text == f"{url}\n\n本文の1行目\n2行目"

    def test_body_only_when_no_source_url(self, tmp_path):
        video = tmp_path / "v.mp4"

        BaseDownloader._save_description(video, _info("本文"))

        assert video.with_suffix(".txt").read_text(encoding="utf-8") == "本文"

    def test_no_file_without_a_description(self, tmp_path):
        video = tmp_path / "v.mp4"

        BaseDownloader._save_description(video, _info(None, "https://example.com/x"))

        assert not video.with_suffix(".txt").exists()


class TestStripLeadingLink:
    def test_link_line_is_not_part_of_the_post_body(self):
        body = "https://www.instagram.com/reel/AAA\n\n『焼きシーザーサラダ🥬』\n\n⚪︎材料"

        assert _strip_leading_link(body).startswith("『焼きシーザーサラダ🥬』")

    def test_body_without_a_link_is_untouched(self):
        body = "『焼きシーザーサラダ🥬』\n\n⚪︎材料"

        assert _strip_leading_link(body) == body

    def test_a_link_further_down_is_kept(self):
        body = "本文\nhttps://example.com/x"

        assert _strip_leading_link(body) == body
