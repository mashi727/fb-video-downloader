"""
Facebook post text extractor

Extracts the body text of a Facebook post from the page HTML,
since yt-dlp does not provide it.
"""

import json
import logging
import re
from html import unescape
from typing import Optional

logger = logging.getLogger(__name__)


class PostTextExtractor:
    """Extract post body text from Facebook page HTML"""

    @classmethod
    def extract(cls, html: str) -> Optional[str]:
        """Extract post text from HTML content using multiple strategies"""
        if not html:
            return None

        # Strategy 1: Extract from JSON data embedded in the page
        text = cls._extract_from_json_data(html)
        if text:
            return text

        # Strategy 2: Extract from meta tags
        text = cls._extract_from_meta_tags(html)
        if text:
            return text

        return None

    @classmethod
    def _extract_from_json_data(cls, html: str) -> Optional[str]:
        """Extract post text from embedded JSON data in Facebook pages"""
        # Facebook embeds post data as JSON in script tags
        # Look for "message" field with "text" subfield
        patterns = [
            # Pattern for message.text in Facebook's relay data
            r'"message"\s*:\s*\{\s*"text"\s*:\s*"((?:[^"\\]|\\.)*)"\s*\}',
            # Pattern for post_text or body in various Facebook JSON structures
            r'"body"\s*:\s*\{\s*"text"\s*:\s*"((?:[^"\\]|\\.)*)"\s*\}',
            # Simpler message pattern
            r'"message"\s*:\s*\{\s*"text"\s*:\s*"((?:[^"\\]|\\.){20,})"\s*[,\}]',
        ]

        best_text = None
        best_length = 0

        for pattern in patterns:
            matches = re.findall(pattern, html)
            for match in matches:
                decoded = cls._decode_json_string(match)
                if decoded and len(decoded) > best_length:
                    # Skip very short texts (likely UI labels)
                    if len(decoded) >= 20:
                        best_text = decoded
                        best_length = len(decoded)

        return best_text

    @classmethod
    def _extract_from_meta_tags(cls, html: str) -> Optional[str]:
        """Extract description from Open Graph meta tags"""
        patterns = [
            r'property="og:description"\s+content="([^"]+)"',
            r'content="([^"]+)"\s+property="og:description"',
            r'name="description"\s+content="([^"]+)"',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                text = unescape(match.group(1))
                # og:description is often truncated, only use if substantial
                if len(text) >= 30:
                    return text

        return None

    @staticmethod
    def _decode_json_string(s: str) -> Optional[str]:
        """Decode a JSON-escaped string"""
        try:
            # Wrap in quotes and parse as JSON string
            decoded = json.loads(f'"{s}"')
            if isinstance(decoded, str):
                return decoded.strip()
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: manual unescape
        try:
            s = s.replace("\\/", "/")
            s = s.replace("\\n", "\n")
            s = s.replace("\\t", "\t")
            s = s.replace('\\"', '"')
            s = s.replace("\\\\", "\\")
            return s.strip()
        except Exception:
            return None
