"""
Main application class
"""

import re
import sys
import logging
import argparse
from pathlib import Path
from typing import List, Optional

from ..downloaders.facebook import FacebookVideoDownloader
from ..downloaders.ytdlp import YtDlpDownloader
from ..utils.validator import URLValidator
from .models import DownloadConfig, DownloadOptions

logger = logging.getLogger(__name__)


class Application:
    """Main application class"""

    def __init__(self):
        self.config = DownloadConfig()
        self.fb_downloader = FacebookVideoDownloader(self.config)
        self.ytdlp_downloader = YtDlpDownloader(self.config)

    def run(self, args: List[str]) -> int:
        """Run the application"""
        parser = self._build_parser()
        try:
            ns = parser.parse_args(args[1:])
        except SystemExit as e:
            return int(e.code or 0)

        options = DownloadOptions(
            audio_only=ns.audio,
            subtitles=ns.subs or ns.srt_only,
            sub_lang=ns.sub_lang,
            srt_only=ns.srt_only,
        )

        self._show_header()

        # Batch mode: a .txt file with one URL per line
        url_arg = Path(ns.url)
        if url_arg.suffix.lower() == ".txt" and url_arg.is_file():
            if ns.output:
                logger.warning("Output filename is ignored in batch mode")
            return self._run_batch(url_arg, options)

        # Clean up URL
        video_url = URLValidator.clean_url(ns.url)
        logger.info(f"Processing URL: {video_url}")

        output_path = Path(ns.output) if ns.output else None

        # Validate URL
        if not URLValidator.validate(video_url):
            return 1

        if self._download_one(video_url, output_path, options):
            logger.info("✓ All processing complete")
            return 0
        else:
            logger.error("✗ Download failed")
            return 1

    def _download_one(
        self,
        video_url: str,
        output_path: Optional[Path],
        options: DownloadOptions,
    ) -> bool:
        """Download a single URL, choosing the appropriate downloader"""
        # Subtitle/audio modes and playlists are yt-dlp only; skip Facebook.
        is_playlist = "list=" in video_url or "/playlist" in video_url
        if options.audio_only or options.subtitles or options.srt_only or is_playlist:
            return self._try_ytdlp(video_url, output_path, options, fallback=False)

        success = self.fb_downloader.download(video_url, output_path, options)
        if not success:
            success = self._try_ytdlp(video_url, output_path, options)
        return success

    def _run_batch(self, txt_path: Path, options: DownloadOptions) -> int:
        """Download every URL listed in a text file (one per line)"""
        urls = self._read_url_list(txt_path)
        if not urls:
            logger.error(f"No URLs found in {txt_path}")
            return 1

        total = len(urls)
        logger.info(f"Batch mode: {total} URL(s) from {txt_path}")

        success_count = 0
        for index, raw_url in enumerate(urls, 1):
            video_url = URLValidator.clean_url(raw_url)
            print("\n" + "=" * 50)
            print(f"[{index}/{total}] {video_url}")
            print("=" * 50)

            if not URLValidator.validate(video_url):
                logger.warning(f"Skipped (invalid URL): {raw_url}")
                continue

            try:
                if self._download_one(video_url, None, options):
                    success_count += 1
                else:
                    logger.warning(f"Failed: {video_url}")
            except Exception as e:
                # One bad URL must not abort the whole batch
                logger.warning(f"Failed: {video_url} ({e})")

        print("\n" + "=" * 50)
        logger.info(f"Batch complete: {success_count}/{total} succeeded")
        print("=" * 50)
        return 0 if success_count > 0 else 1

    @staticmethod
    def _read_url_list(txt_path: Path) -> List[str]:
        """Extract URLs from a text file, skipping blanks and # comments"""
        urls: List[str] = []
        for line in txt_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = re.search(r"https?://\S+", line)
            if match:
                urls.append(match.group(0))
        return urls

    def _try_ytdlp(
        self,
        video_url: str,
        output_path: Optional[Path],
        options: DownloadOptions,
        fallback: bool = True,
    ) -> bool:
        """Download with yt-dlp (as automatic fallback, or directly)"""
        if fallback:
            logger.info("Standard download method failed, trying yt-dlp...")
        else:
            logger.info("Using yt-dlp...")

        try:
            import yt_dlp  # noqa: F401

            clean_url = URLValidator.clean_url(video_url)
            return self.ytdlp_downloader.download(clean_url, output_path, options)
        except ImportError:
            logger.error("yt-dlp is not installed")
            logger.info("To install: pip install yt-dlp")
            return False

    @staticmethod
    def _build_parser() -> argparse.ArgumentParser:
        """Build the command-line argument parser"""
        parser = argparse.ArgumentParser(
            prog="fbdl",
            description="Facebook / Instagram / YouTube video downloader",
            epilog=(
                "Examples:\n"
                "  fbdl https://www.facebook.com/watch/?v=123456789\n"
                "  fbdl 'https://www.facebook.com/reel/123456789' my_video.mp4\n"
                "  fbdl 'https://youtu.be/VIDEO_ID' -a          # audio only (m4a)\n"
                "  fbdl 'https://youtu.be/VIDEO_ID' --subs      # video + subtitles\n"
                "  fbdl 'https://youtu.be/VIDEO_ID' -S          # subtitles only"
            ),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument("url", help="Video URL")
        parser.add_argument("output", nargs="?", help="Output filename (optional)")
        parser.add_argument(
            "-a", "--audio", action="store_true", help="Download audio only (m4a)"
        )
        parser.add_argument(
            "--subs", action="store_true", help="Also download subtitles (SRT)"
        )
        parser.add_argument(
            "-S",
            "--srt-only",
            dest="srt_only",
            action="store_true",
            help="Download subtitles only (no video)",
        )
        parser.add_argument(
            "--sub-lang",
            dest="sub_lang",
            default="ja",
            help="Subtitle language (default: ja)",
        )
        return parser

    @staticmethod
    def _show_header():
        """Show header"""
        print("=" * 50)
        print("Facebook Video Downloader")
        print("=" * 50)
        print("Note: Please comply with copyright laws and Facebook's terms of service")
        print("Only download videos you own or have permission to download\n")


def main():
    """Entry point for console script"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    app = Application()
    sys.exit(app.run(sys.argv))
