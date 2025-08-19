"""
Custom exceptions for Facebook Video Downloader
"""


class DownloaderError(Exception):
    """Base exception for downloader"""

    pass


class VideoNotFoundError(DownloaderError):
    """Exception raised when video is not found"""

    def __init__(self, message: str = "Video not found", url: str = "") -> None:
        self.url = url
        super().__init__(f"{message}: {url}" if url else message)


class NetworkError(DownloaderError):
    """Exception raised for network-related errors"""

    def __init__(self, message: str = "Network error occurred", status_code: int = 0) -> None:
        self.status_code = status_code
        super().__init__(f"{message} (Status: {status_code})" if status_code else message)


class ExtractionError(DownloaderError):
    """Exception raised when video extraction fails"""

    pass


class ValidationError(DownloaderError):
    """Exception raised for validation errors"""

    pass
