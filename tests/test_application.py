"""Tests for CLI argument handling"""

from pathlib import Path

from fb_downloader.core.application import Application


class TestBatchArgument:
    def test_missing_batch_file_is_reported_as_such(self, tmp_path, monkeypatch, caplog):
        """A missing .txt must not be reported as an invalid URL"""
        monkeypatch.chdir(tmp_path)

        code = Application().run(["fbdl", "missing.txt"])

        assert code == 1
        assert "Batch file not found" in caplog.text
        assert "must start with http" not in caplog.text

    def test_directory_named_txt_is_not_treated_as_a_batch_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "d.txt").mkdir()

        assert Application().run(["fbdl", "d.txt"]) == 1

    def test_url_ending_in_txt_is_still_treated_as_a_url(self, tmp_path, monkeypatch):
        """The batch shortcut must not swallow an http URL that ends in .txt"""
        monkeypatch.chdir(tmp_path)
        seen = {}

        app = Application()
        app._download_one = lambda url, out, opts: seen.setdefault("url", url) and True

        app.run(["fbdl", "https://www.facebook.com/watch/list.txt"])

        assert seen["url"].startswith("https://")

    def test_url_list_reads_labels_and_duplicates(self, tmp_path):
        listing = tmp_path / "urls.txt"
        listing.write_text(
            "かぶ\n"
            "https://www.instagram.com/reel/AAA/?igsh=xxx\n"
            "\n"
            "# comment\n"
            "https://www.instagram.com/reel/AAA/?igsh=yyy\n"
            "https://www.instagram.com/reel/BBB/\n",
            encoding="utf-8",
        )

        urls = Application._read_url_list(Path(listing))

        assert urls == [
            "https://www.instagram.com/reel/AAA",
            "https://www.instagram.com/reel/BBB",
        ]
