"""
Main application class
"""

import sys
import logging
from pathlib import Path
from typing import List, Optional

from ..downloaders.facebook import FacebookVideoDownloader
from ..downloaders.ytdlp import YtDlpDownloader
from ..utils.validator import URLValidator
from .models import DownloadConfig

logger = logging.getLogger(__name__)


class Application:
    """Main application class"""

    def __init__(self):
        self.config = DownloadConfig()
        self.fb_downloader = FacebookVideoDownloader(self.config)
        self.ytdlp_downloader = YtDlpDownloader(self.config)

    def run(self, args: List[str]) -> int:
        """Run the application"""
        if len(args) < 2:
            self._show_usage()
            return 1

        video_url = args[1]
        # Clean up URL
        video_url = URLValidator.clean_url(video_url)
        logger.info(f"Processing URL: {video_url}")

        output_path = Path(args[2]) if len(args) > 2 else None

        # Validate URL
        if not URLValidator.validate(video_url):
            return 1

        self._show_header()

        # Download with standard method
        success = self.fb_downloader.download(video_url, output_path)

        # If failed, suggest yt-dlp
        if not success:
            success = self._try_ytdlp(video_url, output_path)

        if success:
            logger.info("✓ All processing complete")
            return 0
        else:
            logger.error("✗ Download failed")
            return 1

    def _try_ytdlp(self, video_url: str, output_path: Optional[Path]) -> bool:
        """Try downloading with yt-dlp"""
        logger.info("Standard download method failed")
        logger.info("Recommend using yt-dlp")

        try:
            import yt_dlp

            response = input("Try downloading with yt-dlp? (y/n): ")
            if response.lower() == "y":
                # Clean URL again (just in case)
                clean_url = URLValidator.clean_url(video_url)
                return self.ytdlp_downloader.download(clean_url, output_path)
        except ImportError:
            logger.info("To install yt-dlp:")
            logger.info("  pip install yt-dlp")
            logger.info("Then you can download directly with:")
            logger.info(f"  yt-dlp {video_url}")

        return False

    @staticmethod
    def _show_usage():
        """Show usage"""
        print("Usage: fbdl <Facebook video URL> [output filename]")
        print("Examples:")
        print("  fbdl https://www.facebook.com/watch/?v=123456789")
        print("  fbdl https://www.facebook.com/share/v/VIDEO_ID/")
        print("  fbdl 'https://www.facebook.com/reel/123456789' my_video.mp4")

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
