"""
Facebook video extractor
"""

import re
import json
import logging
from html import unescape
from typing import Optional, List, Tuple, Dict, Any
from urllib.parse import unquote

from .base import VideoExtractor
from ..core.models import VideoInfo, VideoQuality
from ..core.exceptions import ExtractionError

logger = logging.getLogger(__name__)


class FacebookVideoExtractor(VideoExtractor):
    """Facebook video URL extraction class"""

    # Video URL extraction patterns
    PATTERNS: List[Tuple[str, VideoQuality]] = [
        (r'"hd_src":"([^"]+)"', VideoQuality.HD),
        (r'"sd_src":"([^"]+)"', VideoQuality.SD),
        (r'"video_url":"([^"]+)"', VideoQuality.STANDARD),
        (r'"contentUrl":"([^"]+)"', VideoQuality.STANDARD),
        (r'"playable_url":"([^"]+)"', VideoQuality.STANDARD),
        (r'"playable_url_quality_hd":"([^"]+)"', VideoQuality.HD),
        (r"\"url\":\"([^\"]+\.mp4[^\"]*)", VideoQuality.STANDARD),
        (r'video\.url":"([^"]+)"', VideoQuality.STANDARD),
        (r'"src":"([^"]+\.mp4[^"]*)"', VideoQuality.STANDARD),
    ]

    # Metadata extraction patterns
    METADATA_PATTERNS: Dict[str, List[str]] = {
        "title": [
            r"<title>([^<]+)</title>",
            r'"title":"([^"]+)"',
            r'property="og:title"\s+content="([^"]+)"',
            r'"name":"([^"]+)"',
        ],
        "uploader": [r'"owner":\{"name":"([^"]+)"', r'"author":"([^"]+)"', r'"creator":"([^"]+)"'],
        "description": [
            r'property="og:description"\s+content="([^"]+)"',
            r'"description":"([^"]+)"',
            r'"message":"([^"]+)"',
        ],
        "video_id": [r"/videos/(\d+)", r'"video_id":"(\d+)"', r'"id":"(\d+)"', r"/v/([^/\?]+)"],
    }

    def extract(self, html_content: str) -> Optional[VideoInfo]:
        """Extract video information from HTML content"""
        if not html_content:
            raise ExtractionError("Empty HTML content")

        video_info = None

        # Try to extract JSON-LD structured data first
        video_info = self._extract_from_json_ld(html_content)

        # Fallback to pattern-based extraction
        if not video_info:
            for pattern, quality in self.PATTERNS:
                match = re.search(pattern, html_content)
                if match:
                    video_url = self._clean_url(match.group(1))
                    if self._is_valid_video_url(video_url):
                        logger.info(f"{quality.value} quality video found")
                        video_info = VideoInfo(url=video_url, quality=quality)
                        break

        if not video_info:
            logger.warning("Video URL not found")
            return None

        # Extract metadata
        self._extract_metadata(html_content, video_info)

        return video_info

    def _extract_from_json_ld(self, html_content: str) -> Optional[VideoInfo]:
        """Try to extract video from JSON-LD structured data"""
        json_ld_pattern = r'<script[^>]*type="application/ld\+json"[^>]*>([^<]+)</script>'
        matches = re.findall(json_ld_pattern, html_content)

        for match in matches:
            try:
                data = json.loads(match)
                if isinstance(data, dict) and data.get("@type") == "VideoObject":
                    video_url = data.get("contentUrl")
                    if video_url and self._is_valid_video_url(video_url):
                        return VideoInfo(
                            url=self._clean_url(video_url),
                            quality=VideoQuality.STANDARD,
                            title=data.get("name"),
                            description=data.get("description"),
                            uploader=data.get("author", {}).get("name"),
                        )
            except (json.JSONDecodeError, AttributeError):
                continue
        return None

    def _extract_metadata(self, html_content: str, video_info: VideoInfo) -> None:
        """Extract metadata and add to VideoInfo"""
        for field, patterns in self.METADATA_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    value = self._clean_text(match.group(1))
                    setattr(video_info, field, value)
                    logger.debug(f"{field}: {value[:50]}...")
                    break

    @staticmethod
    def _clean_url(url: str) -> str:
        """Clean up URL"""
        url = unquote(url)
        url = url.replace("\\/", "/")
        return url

    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean up text"""
        # Use html.unescape for proper HTML entity decoding
        text = unescape(text)
        # Replace newlines with spaces
        text = text.replace("\n", " ").replace("\r", " ")
        # Collapse multiple spaces to one
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def _is_valid_video_url(url: str) -> bool:
        """Check if URL is a valid video URL"""
        if not url:
            return False
        # Must be http/https and contain .mp4 or be from Facebook CDN
        return url.startswith(("http://", "https://")) and (
            ".mp4" in url or "video" in url.lower() or "fbcdn" in url or "facebook" in url
        )
