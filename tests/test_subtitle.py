"""Tests for renaming the subtitle yt-dlp writes next to the video"""

from fb_downloader.downloaders.ytdlp import YtDlpDownloader


def _video(tmp_path, name="20260921_トランペット自然奏法.mp4"):
    path = tmp_path / name
    path.write_bytes(b"video")
    return path


class TestFinalizeSubtitle:
    def test_finds_the_name_yt_dlp_actually_writes(self, tmp_path):
        """The outtmpl keeps its extension, so the file is '<base>.mp4.ja.srt'"""
        video = _video(tmp_path)
        (tmp_path / f"{video.name}.ja.srt").write_text("1\n", encoding="utf-8")

        YtDlpDownloader._finalize_subtitle(video, "ja")

        assert (tmp_path / f"{video.stem}_yt.srt").read_text(encoding="utf-8") == "1\n"
        assert not (tmp_path / f"{video.name}.ja.srt").exists()

    def test_still_handles_the_plain_layout(self, tmp_path):
        video = _video(tmp_path)
        (tmp_path / f"{video.stem}.ja.srt").write_text("1\n", encoding="utf-8")

        YtDlpDownloader._finalize_subtitle(video, "ja")

        assert (tmp_path / f"{video.stem}_yt.srt").exists()

    def test_takes_another_language_when_the_requested_one_is_absent(self, tmp_path):
        video = _video(tmp_path)
        (tmp_path / f"{video.name}.en.srt").write_text("1\n", encoding="utf-8")

        YtDlpDownloader._finalize_subtitle(video, "ja")

        assert (tmp_path / f"{video.stem}_yt.srt").exists()

    def test_warns_when_there_is_no_subtitle(self, tmp_path, caplog):
        video = _video(tmp_path)

        YtDlpDownloader._finalize_subtitle(video, "ja")

        assert "No subtitles found" in caplog.text
        assert not (tmp_path / f"{video.stem}_yt.srt").exists()

    def test_an_already_converted_subtitle_is_left_alone(self, tmp_path):
        """The destination must not be picked up as its own source"""
        video = _video(tmp_path)
        done = tmp_path / f"{video.stem}_yt.srt"
        done.write_text("done\n", encoding="utf-8")

        YtDlpDownloader._finalize_subtitle(video, "ja")

        assert done.read_text(encoding="utf-8") == "done\n"
