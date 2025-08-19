"""
Base downloader class
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from requests import Session

from ..core.models import DownloadConfig, VideoInfo
from ..utils.filename import FileNameGenerator


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
    def download(self, url: str, output_path: Optional[Path] = None) -> bool:
        """Download video"""
        pass
    
    def _generate_filename(self, video_info: Optional[VideoInfo] = None) -> str:
        """Auto-generate filename"""
        return FileNameGenerator.generate(video_info)