"""
Facebook Video Downloader Package

A Python package for downloading videos from Facebook.
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .core.application import Application
from .core.exceptions import DownloaderError, VideoNotFoundError, NetworkError
from .core.models import VideoInfo, VideoQuality, DownloadConfig

__all__ = [
    "Application",
    "DownloaderError",
    "VideoNotFoundError",
    "NetworkError",
    "VideoInfo",
    "VideoQuality",
    "DownloadConfig",
]
