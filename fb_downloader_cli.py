#!/usr/bin/env python
"""
Facebook Video Downloader CLI
"""

import sys
import logging
from src.fb_downloader import Application

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def main():
    """Entry point"""
    app = Application()
    sys.exit(app.run(sys.argv))


if __name__ == "__main__":
    main()