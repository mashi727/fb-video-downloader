"""
yt-dlp based downloader
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

from .base import BaseDownloader
from ..core.models import VideoInfo, VideoQuality

logger = logging.getLogger(__name__)


class YtDlpDownloader(BaseDownloader):
    """Downloader using yt-dlp"""

    def download(self, url: str, output_path: Optional[Path] = None) -> bool:
        """Download using yt-dlp"""
        try:
            import yt_dlp
        except ImportError:
            logger.error("yt-dlp is not installed")
            logger.info("To install: pip install yt-dlp")
            return False

        try:
            # First, get video info
            with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
                logger.info(f"Fetching video info: {url}")
                info = ydl.extract_info(url, download=False)

                # Create VideoInfo
                video_info = self._create_video_info(info)

                # Generate filename
                if output_path is None:
                    filename = self._generate_filename(video_info)
                    output_path = Path(filename)

                # Set download options
                ydl_opts = {
                    "outtmpl": str(output_path),
                    "quiet": False,
                    "no_warnings": False,
                    "format": "best",
                    "progress_hooks": [self._progress_hook],
                }

                # Execute download
                with yt_dlp.YoutubeDL(ydl_opts) as ydl_dl:
                    ydl_dl.download([url])

                logger.info(f"✓ Download complete: {output_path}")
                if output_path.exists():
                    logger.info(f"  File size: {output_path.stat().st_size:,} bytes")
                return True

        except Exception as e:
            logger.error(f"yt-dlp error: {e}")
            return False

    @staticmethod
    def _create_video_info(info: Dict[str, Any]) -> VideoInfo:
        """Create VideoInfo from yt-dlp info"""
        return VideoInfo(
            url=info.get("url", ""),
            quality=VideoQuality.STANDARD,
            title=info.get("title"),
            uploader=info.get("uploader") or info.get("channel"),
            description=info.get("description"),
            video_id=str(info.get("id", "")),
        )

    @staticmethod
    def _progress_hook(d: Dict[str, Any]) -> None:
        """Progress display hook"""
        if d["status"] == "downloading":
            print(f"\rProgress: {d.get('_percent_str', '')}", end="")
        elif d["status"] == "finished":
            print()  # New line
