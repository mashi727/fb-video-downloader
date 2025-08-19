"""
Filename generation utility
"""

import re
import unicodedata
from datetime import datetime
from typing import Optional

from ..core.models import VideoInfo


class FileNameGenerator:
    """Filename generation class"""
    
    MAX_FILENAME_LENGTH = 100  # Maximum filename length
    IDEAL_LENGTH = 60  # Ideal length
    
    @classmethod
    def generate(cls, video_info: Optional[VideoInfo] = None) -> str:
        """Generate filename based on video information"""
        if not video_info:
            # If no video info, use timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"fb_video_{timestamp}.mp4"
        
        # Date
        date_str = datetime.now().strftime("%Y%m%d")
        
        # Main content summary
        content_summary = cls._create_content_summary(video_info)
        
        if content_summary:
            # Combine date and content summary
            if video_info.uploader:
                # Include uploader name (shortened)
                uploader = cls._sanitize_filename(video_info.uploader)
                if len(uploader) > 20:
                    uploader = uploader[:20]
                filename = f"{date_str}_{uploader}_{content_summary}"
            else:
                filename = f"{date_str}_{content_summary}"
        else:
            # No content info
            if video_info.video_id:
                filename = f"{date_str}_fb_video_{video_info.video_id[:8]}"
            else:
                timestamp = datetime.now().strftime("%H%M%S")
                filename = f"{date_str}_fb_video_{timestamp}"
        
        # Adjust length
        if len(filename) > cls.MAX_FILENAME_LENGTH:
            # Truncate and add ID
            base = filename[:cls.MAX_FILENAME_LENGTH - 10]
            id_suffix = video_info.video_id[:6] if video_info.video_id else datetime.now().strftime("%H%M")
            filename = f"{base}_{id_suffix}"
        
        return f"{filename}.mp4"
    
    @classmethod
    def _create_content_summary(cls, video_info: VideoInfo) -> str:
        """Create video content summary"""
        # Prioritize title
        if video_info.title:
            return cls._summarize_text(video_info.title, target_length=40)
        
        # Use description if no title
        if video_info.description:
            return cls._summarize_text(video_info.description, target_length=35)
        
        return ""
    
    @classmethod
    def _summarize_text(cls, text: str, target_length: int = 40) -> str:
        """Summarize text meaningfully"""
        # Sanitize
        text = cls._sanitize_filename(text)
        
        # Check for Japanese characters
        has_japanese = any(ord(char) > 0x3000 for char in text)
        
        if has_japanese:
            # For Japanese: consider particles
            parts = re.split(r'[。、！？\s]+', text)
            summary = parts[0] if parts else text
            
            # Truncate if too long
            if len(summary) > target_length:
                summary = summary[:target_length]
                # Remove trailing particles
                particles = 'をにがのでとはも'
                while summary and summary[-1] in particles:
                    summary = summary[:-1]
        else:
            # For English: keep important words
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                         'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
                         'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                         'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'}
            
            # Split into words
            words = text.split('_')
            
            # Select important words
            important_words = []
            current_length = 0
            
            for word in words:
                if word.lower() not in stop_words or len(important_words) == 0:
                    if current_length + len(word) + len(important_words) <= target_length:
                        important_words.append(word)
                        current_length += len(word)
                    else:
                        break
            
            summary = '_'.join(important_words) if important_words else text[:target_length]
        
        return summary
    
    @staticmethod
    def _sanitize_filename(text: str) -> str:
        """Convert to string usable as filename"""
        # Unicode normalization
        text = unicodedata.normalize('NFKC', text)
        
        # Remove or replace invalid characters
        invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
        text = re.sub(invalid_chars, '', text)
        
        # Collapse consecutive spaces/underscores
        text = re.sub(r'[\s_]+', '_', text)
        
        # Remove leading/trailing spaces and symbols
        text = text.strip(' ._-')
        
        # If empty string
        if not text:
            return ""
        
        return text