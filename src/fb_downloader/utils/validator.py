"""
URL validation utility
"""

import re
import logging

logger = logging.getLogger(__name__)


class URLValidator:
    """URL validation class"""
    
    FACEBOOK_DOMAINS = ['facebook.com', 'fb.watch']
    
    @classmethod
    def clean_url(cls, url: str) -> str:
        """Clean up URL"""
        # Remove backslashes and escape sequences
        url = url.replace('\\', '')
        # Fix duplicate slashes
        url = re.sub(r'([^:])//+', r'\1/', url)
        return url
    
    @classmethod
    def validate(cls, url: str) -> bool:
        """Validate URL"""
        if not url.startswith(('http://', 'https://')):
            logger.error("Please enter a valid URL")
            return False
        
        if not any(domain in url for domain in cls.FACEBOOK_DOMAINS):
            logger.warning("This may not be a Facebook URL")
            response = input("Continue? (y/n): ")
            if response.lower() != 'y':
                return False
        
        return True