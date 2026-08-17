"""
Base downloader class
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from requests import Session

from ..core.models import DownloadConfig, DownloadOptions, VideoInfo
from ..utils.filename import FileNameGenerator

logger = logging.getLogger(__name__)


class BaseDownloader(ABC):
    """Abstract base class for downloaders"""

    def __init__(self, config: DownloadConfig):
        self.config = config
        self.session = self._create_session()

    def _create_session(self) -> Session:
        """Create session"""
        session = Session()
        session.headers.update(self.config.headers)
        return session

    @abstractmethod
    def download(
        self,
        url: str,
        output_path: Optional[Path] = None,
        options: Optional[DownloadOptions] = None,
    ) -> bool:
        """Download video"""
        pass

    def _generate_filename(self, video_info: Optional[VideoInfo] = None) -> str:
        """Auto-generate filename"""
        return FileNameGenerator.generate(video_info)

    @staticmethod
    def _ensure_unique_path(path: Path) -> Path:
        """Return a path that does not overwrite an existing file.

        Generated names are date + uploader based, so two videos from the same
        account downloaded on the same day collide — in batch mode that
        silently destroyed the earlier download.
        """
        if not path.exists():
            return path

        for index in range(2, 1000):
            candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
            if not candidate.exists():
                logger.info(f"'{path.name}' exists; saving as '{candidate.name}'")
                return candidate

        return path

    @staticmethod
    def _save_description(output_path: Path, video_info: Optional[VideoInfo]) -> None:
        """Save video description as a text file with the same base name"""
        if video_info is None:
            logger.debug("No video_info available, skipping description save")
            return

        if not video_info.description:
            logger.info("No description found for this video")
            return

        description = video_info.description.strip()
        if not description:
            logger.info("Description is empty")
            return

        txt_path = output_path.with_suffix(".txt")
        try:
            txt_path.write_text(description, encoding="utf-8")
            logger.info(f"✓ Description saved: {txt_path}")
        except OSError as e:
            logger.warning(f"Failed to save description: {e}")
