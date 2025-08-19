"""
Video extractors module
"""

from .base import VideoExtractor
from .facebook import FacebookVideoExtractor

__all__ = ["VideoExtractor", "FacebookVideoExtractor"]
