"""
Setup script for Facebook Video Downloader
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="fb-video-downloader",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A Python package for downloading videos from Facebook",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/fb-video-downloader",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/fb-video-downloader/issues",
        "Documentation": "https://github.com/yourusername/fb-video-downloader#readme",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Video",
        "Topic :: Internet :: WWW/HTTP",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.7",
    install_requires=[
        "requests>=2.31.0",
        "PyYAML>=6.0",
    ],
    extras_require={
        "ytdlp": ["yt-dlp>=2023.10.13"],
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=23.0",
            "flake8>=6.0",
            "mypy>=1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "fbdl=fb_downloader.core.application:main",
        ],
    },
    include_package_data=True,
    package_data={
        "fb_downloader": ["../config/*.yaml"],
    },
)