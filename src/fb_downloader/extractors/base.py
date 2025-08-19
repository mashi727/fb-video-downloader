"""
Base class for video extractors
"""

from abc import ABC, abstractmethod
from typing import Optional

from ..core.models import VideoInfo


class VideoExtractor(ABC):
    """Abstract base class for video URL extraction"""

    @abstractmethod
    def extract(self, html_content: str) -> Optional[VideoInfo]:
        """Extract video information from HTML content"""
        pass
