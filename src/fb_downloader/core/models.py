"""
Data models for Facebook Video Downloader
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict


class VideoQuality(Enum):
    """Video quality enumeration"""
    HD = "HD"
    SD = "SD"
    STANDARD = "標準"
    UNKNOWN = "不明"


@dataclass
class VideoInfo:
    """Data class for storing video information"""
    url: str
    quality: VideoQuality
    size: Optional[int] = None
    title: Optional[str] = None
    uploader: Optional[str] = None
    description: Optional[str] = None
    video_id: Optional[str] = None


@dataclass
class DownloadConfig:
    """Download configuration"""
    chunk_size: int = 8192
    timeout: int = 30
    max_retries: int = 3
    headers: Dict[str, str] = None
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                            'AppleWebKit/537.36 (KHTML, like Gecko) '
                            'Chrome/91.0.4472.124 Safari/537.36'
            }