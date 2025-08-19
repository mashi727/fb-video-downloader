# Facebook Video Downloader

A Python package for downloading videos from Facebook with support for various video qualities and metadata extraction.

## Features

- Download videos from Facebook URLs
- Automatic quality detection (HD/SD)
- Metadata extraction (title, uploader, description)
- Smart filename generation
- Progress tracking
- Fallback to yt-dlp for enhanced compatibility
- Modular and extensible architecture

## Installation

### From GitHub

```bash
git clone https://github.com/yourusername/fb-video-downloader.git
cd fb-video-downloader
pip install -r requirements.txt
```

### Using pip (after setup)

```bash
pip install .
```

## Usage

### Command Line Interface

```bash
# Basic usage
python fb_downloader_cli.py <Facebook_Video_URL>

# With custom output filename
python fb_downloader_cli.py <Facebook_Video_URL> output_video.mp4

# Examples
python fb_downloader_cli.py https://www.facebook.com/watch/?v=123456789
python fb_downloader_cli.py https://www.facebook.com/share/v/VIDEO_ID/
python fb_downloader_cli.py 'https://www.facebook.com/reel/123456789' my_video.mp4
```

### As a Python Module

```python
from fb_downloader import Application

app = Application()
app.run(['fb_downloader', 'https://www.facebook.com/watch/?v=123456789'])
```

### Advanced Usage

```python
from fb_downloader.downloaders import FacebookVideoDownloader
from fb_downloader.core.models import DownloadConfig

# Custom configuration
config = DownloadConfig(
    chunk_size=16384,
    timeout=60,
    max_retries=5
)

# Create downloader
downloader = FacebookVideoDownloader(config)

# Download video
success = downloader.download(
    url='https://www.facebook.com/watch/?v=123456789',
    output_path='my_video.mp4'
)
```

## Project Structure

```
fb-video-downloader/
├── src/
│   └── fb_downloader/
│       ├── core/           # Core components
│       │   ├── application.py
│       │   ├── exceptions.py
│       │   └── models.py
│       ├── extractors/      # Video extractors
│       │   ├── base.py
│       │   └── facebook.py
│       ├── downloaders/     # Download implementations
│       │   ├── base.py
│       │   ├── facebook.py
│       │   └── ytdlp.py
│       └── utils/           # Utilities
│           ├── filename.py
│           ├── progress.py
│           └── validator.py
├── config/                  # Configuration files
│   └── settings.yaml
├── tests/                   # Test files
├── docs/                    # Documentation
├── requirements.txt
├── setup.py
└── README.md
```

## Configuration

The application can be configured via the `config/settings.yaml` file:

```yaml
download:
  chunk_size: 8192
  timeout: 30
  max_retries: 3

headers:
  User-Agent: "Mozilla/5.0..."

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

## Requirements

- Python 3.7+
- requests
- PyYAML
- yt-dlp (optional, for enhanced compatibility)

## Development

### Running Tests

```bash
python -m pytest tests/
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Legal Notice

**Important:** This tool is for educational purposes only. Please ensure you comply with:

- Copyright laws in your jurisdiction
- Facebook's Terms of Service
- Content creators' rights

Only download videos that you own or have explicit permission to download.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Troubleshooting

### Common Issues

1. **Video not found**: The video might be private or the URL format has changed
2. **Network errors**: Check your internet connection and proxy settings
3. **yt-dlp not installed**: Install with `pip install yt-dlp` for better compatibility

### Debug Mode

Enable debug logging by modifying the logging level:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Support

For issues and feature requests, please use the [GitHub Issues](https://github.com/yourusername/fb-video-downloader/issues) page.

## Acknowledgments

- Uses yt-dlp for enhanced video extraction capabilities
- Inspired by various open-source video downloaders