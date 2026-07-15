"""
URL validation utility
"""

import re
import logging
from typing import List, Tuple
from urllib.parse import urlparse

from ..core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class URLValidator:
    """URL validation class"""

    SUPPORTED_DOMAINS: List[str] = [
        "facebook.com",
        "fb.watch",
        "fb.com",
        "facebook.fr",
        "facebook.de",
        "instagram.com",
        "www.instagram.com",
        "youtube.com",
        "youtu.be",
        "m.youtube.com",
        "music.youtube.com",
    ]

    @classmethod
    def clean_url(cls, url: str) -> str:
        """Clean up URL"""
        if not url:
            raise ValidationError("URL cannot be empty")

        # Remove backslashes and escape sequences
        url = url.replace("\\", "")
        # Fix duplicate slashes
        url = re.sub(r"([^:])//+", r"\1/", url)
        # Remove trailing slashes
        url = url.rstrip("/")
        return url

    @classmethod
    def validate(cls, url: str, interactive: bool = True) -> bool:
        """Validate URL"""
        if not url:
            logger.error("URL cannot be empty")
            return False

        if not url.startswith(("http://", "https://")):
            logger.error("Please enter a valid URL (must start with http:// or https://)")
            return False

        try:
            parsed = urlparse(url)
            if not parsed.netloc:
                logger.error("Invalid URL format")
                return False
        except Exception as e:
            logger.error(f"Failed to parse URL: {e}")
            return False

        if not any(domain in parsed.netloc for domain in cls.SUPPORTED_DOMAINS):
            logger.warning("This may not be a supported URL (Facebook/Instagram/YouTube)")
            if interactive:
                try:
                    response = input("Continue? (y/n): ")
                except EOFError:
                    # Non-interactive stdin (piped/batch): don't crash, reject
                    logger.error("No input available; treating unsupported URL as rejected")
                    return False
                if response.lower() != "y":
                    return False
            else:
                return False  # Non-interactive mode: reject unsupported URLs

        return True

    @classmethod
    def extract_video_id(cls, url: str) -> Tuple[str, str]:
        """Extract video ID from URL"""
        patterns = [
            r"/watch/\?v=([0-9]+)",
            r"/videos/([0-9]+)",
            r"/reel/([0-9]+)",
            r"/share/v/([^/]+)",
            r"story_fbid=([0-9]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1), pattern

        return "", ""
