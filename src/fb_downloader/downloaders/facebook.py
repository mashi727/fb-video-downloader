"""
Facebook video downloader
"""

import logging
import time
from pathlib import Path
from typing import Optional

import requests
from requests.exceptions import RequestException, HTTPError, Timeout, ConnectionError

from .base import BaseDownloader
from ..core.exceptions import VideoNotFoundError, NetworkError, ExtractionError
from ..core.models import DownloadConfig, VideoInfo
from ..extractors.facebook import FacebookVideoExtractor
from ..utils.progress import ProgressTracker

logger = logging.getLogger(__name__)


class FacebookVideoDownloader(BaseDownloader):
    """Facebook video downloader"""

    def __init__(self, config: Optional[DownloadConfig] = None):
        super().__init__(config or DownloadConfig())
        self.extractor = FacebookVideoExtractor()

    def download(self, url: str, output_path: Optional[Path] = None) -> bool:
        """Download Facebook video"""
        try:
            # Fetch page
            logger.info(f"Fetching page: {url}")
            html_content = self._fetch_page(url)

            # Extract video info
            video_info = self.extractor.extract(html_content)
            if not video_info:
                raise VideoNotFoundError("Video URL not found")

            # Determine filename
            if output_path is None:
                output_path = Path(self._generate_filename(video_info))

            # Execute download
            self._download_video(video_info, output_path)

            logger.info(f"✓ Download complete: {output_path}")
            logger.info(f"  File size: {output_path.stat().st_size:,} bytes")
            return True

        except (VideoNotFoundError, NetworkError) as e:
            logger.error(f"Download error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False

    def _fetch_page(self, url: str) -> str:
        """Fetch page HTML with retry logic"""
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.get(url, timeout=self.config.timeout)
                response.raise_for_status()
                return response.text
            except HTTPError as e:
                if e.response.status_code == 404:
                    raise VideoNotFoundError(f"Video not found", url=url)
                raise NetworkError(f"HTTP error: {e}", status_code=e.response.status_code)
            except Timeout:
                if attempt < self.config.max_retries - 1:
                    logger.warning(f"Timeout on attempt {attempt + 1}, retrying...")
                    time.sleep(2**attempt)  # Exponential backoff
                    continue
                raise NetworkError("Request timed out after retries")
            except ConnectionError as e:
                raise NetworkError(f"Connection error: {e}")
            except RequestException as e:
                raise NetworkError(f"Failed to fetch page: {e}")

    def _download_video(self, video_info: VideoInfo, output_path: Path) -> None:
        """Download video with progress tracking and error handling"""
        temp_path = output_path.with_suffix(".tmp")

        try:
            logger.info(f"Starting download: {output_path}")

            response = self.session.get(video_info.url, stream=True, timeout=self.config.timeout)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            tracker = ProgressTracker(total_size)

            with open(temp_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=self.config.chunk_size):
                    if chunk:
                        file.write(chunk)
                        tracker.update(len(chunk))

            tracker.complete()

            # Move temp file to final location
            temp_path.rename(output_path)

        except HTTPError as e:
            if temp_path.exists():
                temp_path.unlink()
            raise NetworkError(
                f"HTTP error during download: {e}", status_code=e.response.status_code
            )
        except RequestException as e:
            if temp_path.exists():
                temp_path.unlink()
            raise NetworkError(f"Failed to download video: {e}")
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise
