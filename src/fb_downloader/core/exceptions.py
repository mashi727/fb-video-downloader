"""
Custom exceptions for Facebook Video Downloader
"""


class DownloaderError(Exception):
    """Base exception for downloader"""
    pass


class VideoNotFoundError(DownloaderError):
    """Exception raised when video is not found"""
    pass


class NetworkError(DownloaderError):
    """Exception raised for network-related errors"""
    pass